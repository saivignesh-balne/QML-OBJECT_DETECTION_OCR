const path = require("path");
const esbuild = require("esbuild");

async function main() {
  const root = __dirname;
  await esbuild.build({
    entryPoints: [path.join(root, "frontend", "src", "main.jsx")],
    outfile: path.join(root, "ui_static", "react-app.js"),
    bundle: true,
    format: "iife",
    platform: "browser",
    jsx: "automatic",
    loader: {
      ".js": "jsx",
      ".jsx": "jsx",
    },
    logLevel: "info",
  });
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
