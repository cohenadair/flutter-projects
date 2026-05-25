const vscode = require("vscode");
const path = require("path");

function activate(context) {
  const disposable = vscode.commands.registerCommand(
    "copyForClaude.copySelection",
    async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;

      const selection = editor.selection;
      if (selection.isEmpty) {
        vscode.window.showWarningMessage("Copy for Claude: No text selected.");
        return;
      }

      const document = editor.document;
      const workspaceFolder = vscode.workspace.getWorkspaceFolder(document.uri);

      let relativePath;
      if (workspaceFolder) {
        const fromWorkspace = path.relative(
          workspaceFolder.uri.fsPath,
          document.uri.fsPath
        );
        relativePath = `${workspaceFolder.name}/${fromWorkspace}`;
      } else {
        relativePath = document.uri.fsPath;
      }

      const startLine = selection.start.line + 1;
      const endLine = selection.end.line + 1;
      const lineRef = startLine === endLine ? `${startLine}` : `${startLine}-${endLine}`;
      const result = `@${relativePath}#${lineRef}`;

      await vscode.env.clipboard.writeText(result);
      vscode.window.setStatusBarMessage(`Copied: ${result}`, 3000);
    }
  );

  context.subscriptions.push(disposable);
}

function deactivate() {}

module.exports = { activate, deactivate };
