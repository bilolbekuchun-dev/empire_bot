from aiohttp import web
import os

@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        response = web.Response(status=204)
    else:
        try:
            response = await handler(request)
        except web.HTTPException as ex:
            response = ex
    
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    return response

def setup_webapp_routes(app: web.Application, static_dir: str, bot=None):
    app.middlewares.append(cors_middleware)
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
