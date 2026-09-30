from aiohttp import web
import os

def setup_webapp_routes(app: web.Application, static_dir: str, bot=None):
    index_path = os.path.join(static_dir, "index.html")
    
    if os.path.exists(static_dir):
        app.router.add_static("/static/", path=static_dir, name="static")

    async def index_handler(request):
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600"
        }
        if os.path.exists(index_path):
            return web.FileResponse(index_path, headers=headers)
        return web.Response(text="WebApp API Server Running", headers=headers)

    app.router.add_get("/", index_handler)
    app.router.add_get("/webapp", index_handler)
    app.router.add_get("/webapp/", index_handler)
