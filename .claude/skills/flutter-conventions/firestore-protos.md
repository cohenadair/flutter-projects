# Firestore & protobuf conventions

Part of the `flutter-conventions` skill ([SKILL.md](SKILL.md)).

## Firestore naming & structure

- All Firestore collection names, document paths, and field names must use **camelCase**
  (e.g. `pendingUploads`, `coachId`, `createdAt`). Never use snake_case in Firestore paths
  or field keys.
- Every Firestore document must map **1-to-1 to a protobuf message**. Do not create raw
  Firestore documents (plain `Map` literals) — always define a proto message and serialize
  it via `toFirestoreMap()`.

## Protos

- Canonical import: `package:pro_iq/models/gen/protobuf/pro_iq.pb.dart`
  The `models/gen/` (non-`protobuf/`) path is stale — never use it.
- Proto strings default to `""` when unset, not null. Guard with `.isEmpty`,
  not null checks.
- **Presence checks — field type determines the pattern.** For `string`
  fields, always check `.isEmpty`/`.isNotEmpty` — never the generated
  `has*()` method. For all other field types (numeric, message, enum, etc.),
  use the generated `has*()` method. Do not mix patterns for the same field
  across call sites.
- **Never explicitly set a field to its default value** (`""` for strings, `0`
  or `-1` for numbers, etc.). Generated `has*()` methods must keep working as
  presence checks — explicitly assigning a default value marks the field as
  set, so `has*()` returns `true` even though no real value was written. If a
  value may be absent, only set the field when there's a real value to assign.
- **Every Firestore-backed proto must have `string id = 1;`** as its first field.
  The ID is never stored in Firestore — it is assigned from `snapshot.id` in the
  corresponding `_snapshotTo*` method in `DataManager`:
  ```dart
  Foo? _snapshotToFoo(DocumentSnapshot<Map<String, dynamic>> snapshot) {
    final foo = _snapshotToProtobufType<Foo>(snapshot, () => Foo());
    return foo?..id = snapshot.id;
  }
  ```
  Streams and collections of these types use `List<Foo>`, not `Map<String, Foo>`.
  Never pass a separate `String fooId` alongside a `Foo` object — use `foo.id`.
- **Never store `id` in Firestore.** The `id` field is derived from the document ID
  and must not be stored in the document itself. `toFirestoreMap()` removes it
  automatically — do not call `clearId()` manually.

## Protobuf ↔ Firestore

### Serialization

Always use `toFirestoreMap()` (from `pro_iq/lib/utils/protobuf.dart`) to serialize a proto
object for Firestore. Never manually construct a `Map` from individual proto field values.

### Full-object writes → use `set()`

For document creation and full-object updates, call `set()` — not `update()`:

```dart
Future<void> updateVideo(Video video) =>
    FirestoreWrapper.get.doc("$videosCol/${video.id}").set(video.toFirestoreMap());
```

`toProto3Json()` omits fields at their default value (empty string, 0, empty list). With
`set()` this is correct: omitted fields are absent from the document, which is the desired
state when a field has been cleared. With `update()`, omitted fields are left unchanged,
requiring `FieldValue.delete()` workarounds — avoid this.

### Atomic field mutations → use `update()` with `FieldValue` sentinels

`arrayUnion`, `arrayRemove`, and `increment` are server-side atomic operations that must
remain in `DataManager` as explicit `update()` calls. These operations cannot go through a
proto object because they represent a *delta*, not a full document state.

```dart
// OK — atomic, concurrent-safe, lives in DataManager
Future<void> addFcmToken(String token) {
  final uid = FirebaseAuthWrapper.get.currentUser!.uid;
  return FirestoreWrapper.get.doc("$usersCol/$uid").update({
    "fcmTokens": FieldValue.arrayUnion([token]),
  });
}
```

### DataManager owns all Firestore interaction

Pages and widgets must never:
- Construct raw Firestore field Maps (`{"some_field": value}`)
- Use `FieldValue` sentinels directly
- Reference Firestore collection/document paths

All Firestore writes go through a `DataManager` method. If a page needs to update a field,
add a dedicated method to `DataManager`.

