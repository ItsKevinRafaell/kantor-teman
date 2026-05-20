const { createServer } = require("http");
const { parse } = require("url");
const next = require("next");

const app = next({ dev: false });
const handle = app.getRequestHandler();
const port = process.env.PORT || 3000;

app.prepare().then(() => {
  createServer((req, res) => {
    handle(req, res, parse(req.url, true));
  }).listen(port, () => {
    console.log(`> Ready on port ${port}`);
  });
});
