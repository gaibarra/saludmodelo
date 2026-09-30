const http = require("node:http");
const next = require("next");
const app = next({
  dev: true,
  hostname: "127.0.0.1",
  port: Number(process.env.E2E_FRONTEND_PORT),
});
app
  .prepare()
  .then(() => {
    const server = http.createServer(app.getRequestHandler());
    server.listen({ fd: Number(process.env.E2E_FRONTEND_FD) });
  })
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
