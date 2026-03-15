import discord
from discord.ext import commands, tasks
import smtplib
from email.message import EmailMessage
import sys
from random import randint
import os
from pymata4 import pymata4
import time
import ffmpeg

with open("./token.txt", "r", encoding="utf-8") as fichier:
    token = fichier.readline()
    ##########################################################################
    # Configuration de l'email pour la 2FA
    ##########################################################################
    EMAIL_ADDRESS = fichier.readline()  # Remplacez par votre adresse Gmail
    EMAIL_PASSWORD = fichier.readline()  # Mot de passe d'application Gmail
    AUTH_EMAIL = fichier.readline()  # Adresse email autorisée pour la vérification

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(intents=intents, command_prefix="!")

verification_codes = {}  # Stocke les codes de vérification par utilisateur
verified_users = {}      # Stocke l'état de vérification des utilisateurs

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

##########################################################################
# Vérificateur de 2FA pour chaque commande
##########################################################################
async def check_2fa(ctx):
    if ctx.author.id not in verified_users or not verified_users[ctx.author.id]:
        print(f"{ctx.author.name} à essayer de faire un commande mais n'est pas identifié.")
        return False
    return True

##########################################################################
# Commandes de vérification
##########################################################################
@bot.command(name="verifier")
async def verifier(ctx):
    code = randint(100000, 999999)
    verification_codes[ctx.author.id] = code
    send_verification_email(AUTH_EMAIL, code)  # Toujours envoyer à l'email autorisé
    await ctx.reply(f"Code de vérification envoyé à {AUTH_EMAIL}. Veuillez vérifier votre boîte de réception.")

@bot.command(name="confirmer")
async def confirmer(ctx, code: int):
    if ctx.author.id in verification_codes and verification_codes[ctx.author.id] == code:
        verified_users[ctx.author.id] = True
        del verification_codes[ctx.author.id]  # Supprime le code après vérification réussie
        await ctx.reply("Vérification réussie !")
    else:
        await ctx.reply("Code incorrect ou expiré.")

def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = int(f.read())
        return temp / 1000.0
    except:
        return None
        
##########################################################################
# Status update
##########################################################################
@tasks.loop(seconds=60)
async def status_update():
    vals = carte.dht_read(Temp_pin)
    humi = vals[0]
    temp = vals[1]
    cpu = get_cpu_temp()
    if humi is None:
        humi = "N/A"
    if temp is None:
        temp = "N/A"
    if cpu is None:
        cpu = "N/A"
    await bot.change_presence(activity=discord.Game(name=f"CPU {cpu:.1f} | AIR {temp:.1f}°C | Humidité {humi:.2f}%"))

##########################################################################
# à la connexion
##########################################################################
@bot.event
async def on_ready():
    channel = discord.utils.get(bot.get_all_channels(), name="bot-pc")  # Remplacer "bot-pc" par le nom du salon du serveur
    await bot.get_channel(channel.id).send("Bonjour à tous !")
    print(f"{bot.user.name} est prêt.")
    status_update.start()

##########################################################################
# en cas d'erreur
##########################################################################
@bot.event
async def on_command_error(ctx, error):
    if await check_2fa(ctx):
        if isinstance(error, commands.CommandNotFound):
            await ctx.reply("Vérifier votre commande.")
        else:
            raise error

##########################################################################
# Test bot
##########################################################################
@bot.command(name="hello")
async def hello(ctx):
    if await check_2fa(ctx):
        await ctx.reply(f"hello, {ctx.author.name}")

##########################################################################
# allumer
##########################################################################
@bot.command(name="allumer")
async def allumer(ctx):
    if await check_2fa(ctx):
        reponse = "Led allumé."
        await ctx.reply(reponse)
        # carte.digital_write(Led_bleue, 1)
        carte.servo_write(Servo_pin, 130)
        time.sleep(1)
        carte.servo_write(Servo_pin, 90)
        print(f"Réponse à message {ctx.message.id} : {reponse}")

##########################################################################
# maintenir
##########################################################################
@bot.command(name="maintenir")
async def allumer(ctx):
    if await check_2fa(ctx):
        reponse = "Led éteinte de force"
        await ctx.reply(reponse)
        # carte.digital_write(Led_bleue, 1)
        carte.servo_write(Servo_pin, 130)
        time.sleep(6)
        carte.servo_write(Servo_pin, 90)
        carte.digital_write(Led_bleue, 0)
        print(f"Réponse à message {ctx.message.id} : {reponse}")

##########################################################################
# eteindre
##########################################################################
@bot.command(name="eteindre")
async def eteindre(ctx):
    if await check_2fa(ctx):
        reponse = "Led éteinte."
        await ctx.reply(reponse)
        # carte.digital_write(Led_bleue, 0)
        print(f"Réponse à message {ctx.message.id} : {reponse}")
############################################################################
# Curl Led Cam (commande optionnelle pour allumer/éteindre la led de la cam
# changer <url_led_de_la_cam> avec la vrai url de votre cam
############################################################################
#@bot.command(name="curl")
#async def curl(ctx):
#	reponse = "Led dans son état opposé"
#	await ctx.reply(reponse)
#	print(f"Reponse à message {ctx.message.id} : {reponse}"
#	os.system("curl <url_led_de_la_cam>")
#
##########################################################################
# quitter
##########################################################################
@bot.command(name="quitter")
async def quitter(ctx):
    if await check_2fa(ctx):
        reponse = "Bot déconnecté. Bye Bye !"
        await ctx.reply(reponse)
        await bot.close()
        carte.shutdown()
        print(f"Réponse à message {ctx.message.id} : {reponse}")
        print("--------------- Fin --------------")

##########################################################################
# reboot
##########################################################################
@bot.command(name="reboot")
async def quitter(ctx):
    if await check_2fa(ctx):
        reponse = "Bot déconnecté il va redémarrer dans quelque instants. A de suite !"
        await ctx.reply(reponse)
        await bot.close()
        carte.shutdown()
        print(f"Réponse à message {ctx.message.id} : {reponse}")
        print("--------------- Fin --------------")
        os.system("sudo reboot")

##########################################################################
# Supprimer tous les messages : !purger
##########################################################################
@bot.command(name="purger")
async def purge(ctx):
    if await check_2fa(ctx):
        await ctx.channel.purge()

##########################################################################
# Envoyer une image
##########################################################################
@bot.command(name="picture")
async def picture(ctx):
    if await check_2fa(ctx):
        carte.digital_write(Led_bleue, 1)
        #await ctx.reply('Capture de la cam...')
        #os.system('sudo libcamera-still -o image.jpg')
        time.sleep(3)
        await ctx.reply('envoie de la capture :')
        await ctx.channel.send(file=discord.File('image.jpg'))
        carte.digital_write(Led_bleue, 0)

#############################################################################
# Stream motion_eye (pour utilisation compléter <url_stream> et <id_channel>
#############################################################################
#@bot.command(name="stream")
#async def stream(ctx):
#    """Commande pour démarrer le streaming"""
#    if ctx.voice_client:  # Vérifie si le bot est déjà dans un canal vocal
#        await ctx.voice_client.disconnect()
#
#    channel = bot.get_channel(<id_channel>)
#    if isinstance(channel, discord.VoiceChannel):
#        vc = await channel.connect()
#        ffmpeg_process = (
#            ffmpeg
#            .input("<url_stream>")
#            .output("pipe:1", format="opus", acodec="libopus", audio_bitrate="64k")
#            .run_async(pipe_stdout=True)
#        )
#
#        while not ffmpeg_process.poll():
#            data = ffmpeg_process.stdout.read(4000)
#            if vc.is_connected():
#                vc.send_audio_packet(data)
#            await asyncio.sleep(0.02)
#
#        await vc.disconnect()

##########################################################################
# Initialisations de Pymata et exécution du bot
##########################################################################
carte = pymata4.Pymata4()
print("--------------- Début --------------")

# Constantes
Led_bleue = 13  # Led
Servo_pin = 10
Temp_pin = 2

carte.set_pin_mode_dht(Temp_pin, sensor_type=11)
carte.set_pin_mode_digital_output(Led_bleue)
carte.digital_write(Led_bleue, 0)
carte.set_pin_mode_servo(Servo_pin)
carte.servo_write(Servo_pin, 90)
time.sleep(3)

bot.run(token)

