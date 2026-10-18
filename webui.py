"""Serveur web de ControlBot.

Tourne dans la même boucle asyncio que le bot Discord : les deux interfaces
appellent exactement les mêmes actions (voir `actions` dans bot.py).
"""
import hmac
import secrets
import time
from pathlib import Path

from aiohttp import web

WEB_DIR = Path(__file__).parent / "web"
COOKIE = "controlbot_session"
SESSION_TTL = 12 * 3600      # durée d'une session : 12 h
MAX_FAILS = 5                # tentatives de mot de passe avant blocage
LOCKOUT_SECONDS = 60


def create_app(password: str, actions: dict, get_status, get_picture_path) -> web.Application:
    """
    password         : mot de passe de l'interface web
    actions          : {"allumer": async fn -> str, ...}
    get_status       : fn -> dict
    get_picture_path : fn -> chemin de l'image à servir
    """
    sessions: dict[str, float] = {}
    fails: dict[str, list] = {}  # ip -> [compteur, dernier échec]

    @web.middleware
    async def auth_middleware(request, handler):
        if request.path.startswith("/api/") and request.path != "/api/login":
            token = request.cookies.get(COOKIE)
            expires = sessions.get(token)
            if not expires or expires < time.time():
                sessions.pop(token, None)
                return web.json_response({"error": "Non authentifié"}, status=401)
        return await handler(request)

    async def index(request):
        return web.FileResponse(WEB_DIR / "index.html")

    async def login(request):
        ip = request.remote or "?"
        count, last = fails.get(ip, [0, 0.0])
        if count >= MAX_FAILS and time.time() - last < LOCKOUT_SECONDS:
            return web.json_response({"error": "Trop de tentatives, patientez 1 minute."}, status=429)

        try:
            data = await request.json()
        except Exception:
            data = {}
        given = str(data.get("password", ""))

        if not hmac.compare_digest(given.encode(), password.encode()):
            fails[ip] = [count + 1 if time.time() - last < LOCKOUT_SECONDS else 1, time.time()]
            return web.json_response({"error": "Mot de passe incorrect."}, status=401)

        fails.pop(ip, None)
        token = secrets.token_urlsafe(32)
        sessions[token] = time.time() + SESSION_TTL
        resp = web.json_response({"ok": True})
        resp.set_cookie(COOKIE, token, max_age=SESSION_TTL, httponly=True, samesite="Strict")
        return resp

    async def logout(request):
        sessions.pop(request.cookies.get(COOKIE), None)
        resp = web.json_response({"ok": True})
        resp.del_cookie(COOKIE)
        return resp

    async def status(request):
        return web.json_response(get_status())

    async def run_action(request):
        name = request.match_info["name"]
        action = actions.get(name)
        if action is None:
            return web.json_response({"error": "Action inconnue"}, status=404)
        try:
            message = await action()
        except Exception as e:  # on remonte l'erreur à l'interface
            return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=500)
        return web.json_response({"ok": True, "message": message})

    async def picture(request):
        path = Path(get_picture_path())
        if not path.exists():
            return web.json_response({"error": "image.jpg introuvable"}, status=404)
        return web.FileResponse(path, headers={"Cache-Control": "no-store"})

    app = web.Application(middlewares=[auth_middleware])
    app.router.add_get("/", index)
    app.router.add_post("/api/login", login)
    app.router.add_post("/api/logout", logout)
    app.router.add_get("/api/status", status)
    app.router.add_get("/api/picture", picture)
    app.router.add_post("/api/action/{name}", run_action)
    app.router.add_static("/static/", WEB_DIR, show_index=False)
    return app
