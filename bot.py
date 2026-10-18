import asyncio
import os
import smtplib
import time
from email.message import EmailMessage
from random import randint

import discord
import RPi.GPIO as GPIO
from aiohttp import web
from discord.ext import commands, tasks
from pymata4 import pymata4

import webui

##########################################################################
# Configuration
##########################################################################
CHANNEL_NAME = "bot-pc"      # salon Discord utilisé pour le message de démarrage et la purge
WEB_HOST = "0.0.0.0"         # "127.0.0.1" = accessible uniquement depuis cette machine
WEB_PORT = 8080

# GPIO utilisé pour le ventilateur
FAN_PIN = 18
fan_state = False

# Broches Arduino
Led_bleue = 13
Servo_pin = 10
Temp_pin = 2

##########################################################################
# Ventilateur
##########################################################################
def init_fan():
    global fan_state
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(FAN_PIN, GPIO.OUT)
    GPIO.output(FAN_PIN, GPIO.LOW)
    fan_state = False

def turn_fan_on():
    global fan_state
    GPIO.output(FAN_PIN, GPIO.HIGH)
    fan_state = True

def turn_fan_off():
    global fan_state
    GPIO.output(FAN_PIN, GPIO.LOW)
    fan_state = False

def cleanup_fan():
    GPIO.output(FAN_PIN, GPIO.LOW)
    GPIO.cleanup()

##########################################################################
# Lecture de token.txt
# Lignes : 1 token Discord, 2 Gmail, 3 mot de passe d'app, 4 email 2FA,
#          5 mot de passe de l'interface web (optionnel : sans lui, pas de web)
##########################################################################
with open("./token.txt", "r", encoding="utf-8") as fichier:
    token = fichier.readline().strip()
    EMAIL_ADDRESS = fichier.readline().strip()
    EMAIL_PASSWORD = fichier.readline().strip()
    AUTH_EMAIL = fichier.readline().strip()
    WEB_PASSWORD = fichier.readline().strip()

##########################################################################
# Bot
##########################################################################
class ControlBot(commands.Bot):
    web_runner = None

    async def setup_hook(self):
        global hw_lock
        hw_lock = asyncio.Lock()  # créé dans la boucle du bot
        if WEB_PASSWORD:
            app = webui.create_app(
                WEB_PASSWORD, ACTIONS, get_status, lambda: "image.jpg"
            )
            self.web_runner = web.AppRunner(app)
            await self.web_runner.setup()
            await web.TCPSite(self.web_runner, WEB_HOST, WEB_PORT).start()
            print(f"Interface web : http://{WEB_HOST}:{WEB_PORT}")
        else:
            print("Ligne 5 de token.txt absente : interface web désactivée.")

    async def close(self):
        if self.web_runner:
            await self.web_runner.cleanup()
            self.web_runner = None
        await super().close()

intents = discord.Intents.default()
intents.message_content = True
bot = ControlBot(intents=intents, command_prefix="!")

verification_codes = {}
verified_users = {}
hw_lock = None  # défini dans setup_hook

# Dernières mesures, partagées entre Discord et le web
state = {"temp": None, "humi": None, "cpu": None}

##########################################################################
# 2FA par email (Discord)
##########################################################################
def send_verification_email(to_email, code):
    msg = EmailMessage()
    msg.set_content(f"Votre code de vérification est : {code}")
    msg["Subject"] = "Code de vérification pour le bot Discord"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
    print(f"Code de vérification envoyé à {to_email}")

async def check_2fa(ctx):
    if not verified_users.get(ctx.author.id):
        print(f"{ctx.author.name} a essayé de faire une commande mais n'est pas identifié.")
        return False
    return True

@bot.command(name="verifier")
async def verifier(ctx):
    code = randint(100000, 999999)
    verification_codes[ctx.author.id] = code
    send_verification_email(AUTH_EMAIL, code)
    await ctx.reply(f"Code de vérification envoyé à {AUTH_EMAIL}. Veuillez vérifier votre boîte de réception.")

@bot.command(name="confirmer")
async def confirmer(ctx, code: int):
    if verification_codes.get(ctx.author.id) == code:
        verified_users[ctx.author.id] = True
        del verification_codes[ctx.author.id]
        await ctx.reply("Vérification réussie !")
    else:
        await ctx.reply("Code incorrect ou expiré.")

##########################################################################
# Actions partagées (Discord ET web)
# Chaque action est async et protégée par hw_lock : si on clique sur le web
# pendant qu'une commande Discord tourne, elles passent l'une après l'autre.
# Important : asyncio.sleep (et non time.sleep) pour ne pas figer le bot
# ni le serveur web pendant l'appui sur le bouton.
##########################################################################
async def action_allumer():
    async with hw_lock:
        carte.servo_write(Servo_pin, 130)
        await asyncio.sleep(1)
        carte.servo_write(Servo_pin, 90)
    return "Appui court effectué."

async def action_maintenir():
    async with hw_lock:
        carte.servo_write(Servo_pin, 130)
        await asyncio.sleep(6)
        carte.servo_write(Servo_pin, 90)
        carte.digital_write(Led_bleue, 0)
    return "Appui long effectué (extinction forcée)."

async def action_eteindre():
    # À compléter selon ton câblage
    return "Extinction (non câblée pour l'instant)."

async def action_picture():
    async with hw_lock:
        carte.digital_write(Led_bleue, 1)
        # os.system('sudo libcamera-still -o image.jpg')
        await asyncio.sleep(3)
        carte.digital_write(Led_bleue, 0)
    return "Capture prête."

async def action_purger():
    channel = discord.utils.get(bot.get_all_channels(), name=CHANNEL_NAME)
    if channel is None:
        raise RuntimeError(f"Salon '{CHANNEL_NAME}' introuvable")
    await channel.purge()
    return "Salon purgé."

async def _shutdown(reboot: bool):
    await asyncio.sleep(1)  # laisse le temps d'envoyer la réponse HTTP/Discord
    await bot.close()
    carte.shutdown()
    print("--------------- Fin --------------")
    if reboot:
        os.system("sudo reboot")

async def action_quitter():
    asyncio.create_task(_shutdown(False))
    return "Bot déconnecté. Bye Bye !"

async def action_reboot():
    asyncio.create_task(_shutdown(True))
    return "Redémarrage en cours…"

ACTIONS = {
    "allumer": action_allumer,
    "maintenir": action_maintenir,
    "eteindre": action_eteindre,
    "picture": action_picture,
    "purger": action_purger,
    "quitter": action_quitter,
    "reboot": action_reboot,
}

def get_status():
    return {**state, "fan": fan_state, "updated": time.time()}

##########################################################################
# Température CPU + statut
##########################################################################
def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return int(f.read()) / 1000.0
    except Exception:
        return None

def fmt(value, spec):
    return "N/A" if value is None else format(value, spec)

@tasks.loop(seconds=60)
async def status_update():
    temp = humi = None
    try:
        vals = carte.dht_read(Temp_pin)
        humi, temp = vals[0], vals[1]
    except Exception as e:
        print(f"Lecture DHT impossible : {e}")
    cpu = get_cpu_temp()
    state.update(temp=temp, humi=humi, cpu=cpu)

    FAN_ON, FAN_OFF = 55, 45
    if cpu is not None:
        if cpu >= FAN_ON and not fan_state:
            turn_fan_on()
        elif cpu <= FAN_OFF and fan_state:
            turn_fan_off()

    await bot.change_presence(activity=discord.Game(
        name=f"CPU {fmt(cpu, '.1f')}°C | FAN {'ON' if fan_state else 'OFF'} | "
             f"AIR {fmt(temp, '.1f')}°C | Humidité {fmt(humi, '.2f')}%"
    ))

##########################################################################
# Événements
##########################################################################
@bot.event
async def on_ready():
    channel = discord.utils.get(bot.get_all_channels(), name=CHANNEL_NAME)
    if channel:
        await channel.send("Bonjour à tous !")
    print(f"{bot.user.name} est prêt.")
    if not status_update.is_running():  # on_ready peut être rappelé après une reconnexion
        init_fan()
        status_update.start()

@bot.event
async def on_command_error(ctx, error):
    if await check_2fa(ctx):
        if isinstance(error, commands.CommandNotFound):
            await ctx.reply("Vérifier votre commande.")
        else:
            raise error

##########################################################################
# Commandes Discord (déléguent aux actions partagées)
##########################################################################
@bot.command(name="hello")
async def hello(ctx):
    if await check_2fa(ctx):
        await ctx.reply(f"hello, {ctx.author.name}")

@bot.command(name="allumer")
async def cmd_allumer(ctx):
    if await check_2fa(ctx):
        await ctx.reply("Led allumé.")
        await action_allumer()

@bot.command(name="maintenir")
async def cmd_maintenir(ctx):
    if await check_2fa(ctx):
        await ctx.reply("Led éteinte de force")
        await action_maintenir()

@bot.command(name="eteindre")
async def cmd_eteindre(ctx):
    if await check_2fa(ctx):
        await ctx.reply(await action_eteindre())

@bot.command(name="quitter")
async def cmd_quitter(ctx):
    if await check_2fa(ctx):
        await ctx.reply(await action_quitter())

@bot.command(name="reboot")
async def cmd_reboot(ctx):
    if await check_2fa(ctx):
        await ctx.reply("Bot déconnecté il va redémarrer dans quelques instants. À de suite !")
        await action_reboot()

@bot.command(name="purger")
async def purge(ctx):
    if await check_2fa(ctx):
        await ctx.channel.purge()

@bot.command(name="picture")
async def picture(ctx):
    if await check_2fa(ctx):
        await action_picture()
        await ctx.reply("envoi de la capture :")
        await ctx.channel.send(file=discord.File("image.jpg"))

##########################################################################
# Initialisation Pymata et exécution du bot
##########################################################################
carte = pymata4.Pymata4()
print("--------------- Début --------------")

carte.set_pin_mode_dht(Temp_pin, sensor_type=11)
carte.set_pin_mode_digital_output(Led_bleue)
carte.digital_write(Led_bleue, 0)
carte.set_pin_mode_servo(Servo_pin)
carte.servo_write(Servo_pin, 90)
time.sleep(3)

bot.run(token)
