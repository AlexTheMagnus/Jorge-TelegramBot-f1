#!/usr/bin/env python
# -*- coding: utf-8 -*-
import telebot
from libs import comp_func as comp
from libs import user_func as user
from libs import time_func as timef
from libs import aux
from libs import rank_func
from libs.keyboard import *
import private as tk
import random



#CONFIGURACIÓN DE TELEGRAM
token = tk.tk()
bot = telebot.TeleBot(token)


#Simplifica el enviar
def send(m, message_text):
    bot.send_message(m.chat.id, message_text)

def sendMarkdownMessage(cid, message_text):
    bot.send_message(cid, message_text, parse_mode="Markdown")


#Crea una competicion
@bot.message_handler(commands=['st_comp'])
def new_competition(m):
    #Este comando crea la competición y manda el seleccionador de equipos
    cid = m.chat.id #Chat_id
    cname = m.chat.title #Nombre del chat
    uid = m.from_user.id
    #Para comprobar si el chat es un grupo o no, miramos su id (los grupos tienen id negativa)
    if cid > 0:
        send(m, "Error!! Debes crear la competicion en un grupo")
    elif cid < 0:
        if comp.existe_comp(cid):
            send(m, "Ya hay una competicion en este grupo")
        else:
            comp.create_comp(cid)
            send(m, "La competicion se ha creado")
            #Establece al creador de la competición como administrador de la misma
            comp.add_admin(cid, uid, cname)
            #Manda el mensaje de los equipos con el teclado cuando se crea la competición
            message = bot.send_message(cid, keyboard_message(cid), reply_markup = keyboard_team)
            mid = message.message_id
            bid = message.from_user.id
            #Los campos como can_pin_messages solo existen en el objeto ChatMember
            botMember = bot.get_chat_member (cid, bid)
            #Si el bot tiene capacidad para anclar mensajes, lo ancla, si no, manda un mensaje
            if botMember.can_pin_messages or botMember.can_edit_messages:
                bot.pin_chat_message (cid, mid)
            else: send(m, 'Si conviertes el grupo en un supergrupo, me haces administrador '
                          'con derecho a anclar mensajes y vuelves a crear la competición, '
                          'puedo anclar el mensaje de los equipos con el teclado al grupo')
            #Abre el chat privado con el admin
            bot.send_message(uid, "Desde este chat, podras administrar tus competiciones usando /my_comps")
    else:
            print "Se produjo un fallo E:001"

#Maneja las respuestas del teclado, entra cada vez que alguien clicka una opción
@bot.callback_query_handler(func = lambda team: team.data in ["mercedes", "red_bull", "williams", "ferrari", "mclaren", "force_india", "toro_rosso", "lotus", "sauber", "marussia"])
def join_in(team):
    cid = team.message.chat.id
    uid = team.from_user.id
    mid = team.message.message_id
    unick = team.from_user.username
    uteam = team.data #Equivale al valor de la lista que se corresponde con el botón clickado
    if comp.existe_comp(cid):
        if user.existe_user(uid, cid):
            if user.team_full(cid, uteam):
                message = "Ese equipo esta lleno " + unick + ", elige uno con menos de 2 pilotos"
                bot.send_message(team.message.chat.id, message)
            else:
                #Si el usuario que clicka ya está en la competición y el equipo
                #que selecciona no está lleno, lo cambia de equipo
                if(user.change_team(cid, uid, uteam)):
                    #Actualiza el mensaje que acompaña al teclado, su estructura está
                    #en libs/keyboard.py
                    bot.edit_message_text(keyboard_message(cid), cid, mid, reply_markup = keyboard_team)
        else:
            if user.team_full(cid, uteam):
                message = "Ese equipo esta lleno " + unick + ", elige uno con menos de 2 pilotos"
                bot.send_message(team.message.chat.id, message)

            else:
                #Para un usuario nuevo, que selecciona un equipo que no está lleno
                #mete los campos necesarios en la base de datos
                user.join_in(cid, uid, unick, uteam)
                #Actualiza el mensaje que acompaña al teclado, su estructura está
                #en libs/keyboard.py
                bot.edit_message_text(keyboard_message(cid), cid, mid, reply_markup = keyboard_team)
    else:
        bot.send_message(team.message.chat.id, "No hay competicion en este grupo todavia")
        bot.send_message(team.message.chat.id, "Puedes empezar una con /st_comp")

@bot.message_handler(commands=['dl_comp'])
def dl_competition(m):
    #Este comando permite eliminar una competición
    cid = m.chat.id
    uid = m.from_user.id
    uname = m.from_user.first_name
    if comp.existe_comp(cid):
        if user.is_admin(cid, uid):
            comp.delete_comp(cid, uid)
            send(m, "La competicion ha sido eliminada")
        else:
            message = uname + " no tiene permisos para realizar esa operacion"
            send(m, message)

    else:
        send(m, "No existe competicion todavía")
        send(m, "Puedes empezar una con /st_comp")

@bot.message_handler(commands=['time'])
def time(m):
    cid = m.chat.id
    uid = m.from_user.id
    uname = m.from_user.username
    # time = telebot.util.extract_arguments(m.text)
    splitm = m.text.split()
    if len(splitm) == 2:
        time = splitm[1]
    else:
        time = 'invalid'

    if comp.existe_comp(cid):
        if timef.add_time(cid, uid, time):
            msg = uname + " ha agregado su tiempo"
            send(m, msg)
        else:
            send(m, "No se ha podido agregar el tiempo [Error de formato]")
            send(m, 'Usa /time + tiempo(MM:ss:mmm)')
    else:
        send(m, "No hay ninguna competición en este grupo")
        send(m, "Puedes empezar una con /st_comp")


@bot.message_handler(commands=['race_info'])
def next_race(m):
    #Este comando nos dará información sobre la próxima carrera
    cid = m.chat.id

    if comp.existe_comp(cid):
        race = comp.get_race_bycomp(cid)

        sendMarkdownMessage(cid, """
            🚥 *Próxima Carrera* 🚥

            *Nombre: * {}
            *Vueltas: * {}

        """.format(race['nombre'], race['long']))

        bot.send_photo(cid, "%s"%(race['image']))


@bot.callback_query_handler(func=lambda callback: aux.is_to_list(callback.data, 2)
                                                  and aux.to_list(callback.data, 2)[0][1:].isdigit())
def send_penal(callback):
    args = aux.to_list(callback.data, 2)
    compid, pid = args[0], args[1]
    cid = callback.message.chat.id
    bot.delete_message(cid, callback.message.message_id)
    keyboard_penal = get_keyboardPenal(compid, pid)
    bot.send_message(cid, 'Elige la penalizacion', reply_markup=keyboard_penal)


@bot.message_handler(commands=['end_race'])
def end_race(m):
    # Este comando es uno de los mas importantes
    # Dará por terminada la carrera, sumará los puntos e imprimirá la clasificación
    # También dejará todos los tiempos a 0 de nuevo
    cid = m.chat.id
    uid = m.from_user.id
    uname = m.from_user.username

    if comp.existe_comp(cid):
        if user.is_admin(cid, uid):
            # Comprobamos que todos los juagdores han metido su tiempo
            if timef.all_times_defined(cid):
                send(m, "La carrera ha terminado")
                # Damos los puntos a los jugadores
                #Y mostramos las clasificaciones de la carrera y el campeonato
                timef.give_points(cid)
                lrace_info(m)
                clasif_info(m)
                #Se termina la carrera y muestra información sombre la siguiente
                comp.plus_race_bycomp(cid)
                timef.reset_time(cid)
                next_race(m)
            else:
                send(m, "Todos los pilotos no han metido su tiempo, pueden hacerlo con /time <M:S:MM>")
        else:
            message = uname + " no tiene permisos para realizar esa operacion"
            send(m, message)
    else:
        send(m, 'No hay competicion en este grupo')
        send(m, 'Puedes crear una con /st_comp')


@bot.message_handler(commands=['my_comps'])
def my_comps(m):
    # Primer paso de la herramienta que permite administrar una competición
    cid = m.chat.id
    uid = m.from_user.id

    if cid > 0:
        if user.have_comps(uid): #Mira si es admin de alguna competicion
            keyboard_comps = get_keyboardAdmin(uid) #Devuelve un teclado con las competiciones
            bot.send_message(cid, "Selecciona la competicion a administrar", reply_markup=keyboard_comps)

            #Habrá que esperar una respuesta y seguir
        else:
            send(m, "No eres administrador de ninguna competicion")
    else:
        send(m, "Ese comando solo puede usarse desde un chat privado")


@bot.callback_query_handler(func=lambda callback: callback.data in comp.comp_list())
def send_options(callback):
    cid = callback.message.chat.id
    compid = callback.data
    keyboard_opts = get_keyboardOptions(compid)
    bot.delete_message(cid, callback.message.message_id)
    bot.send_message(cid, "Elige una opcion", reply_markup=keyboard_opts)


@bot.callback_query_handler(func=lambda callback: aux.is_to_list(callback.data, 2)
                                                  and aux.to_list(callback.data, 2)[0] == 'Penalizar')
def send_players(callback):
    compid = aux.to_list(callback.data, 2)[1]
    cid = callback.message.chat.id
    keyboard_players = get_keyboardPlayers(compid)
    bot.delete_message(cid, callback.message.message_id)
    bot.send_message(cid, u'Elige a quién penalizar', reply_markup=keyboard_players)


@bot.callback_query_handler(func=lambda callback: aux.is_to_list(callback.data, 3))
def penalizar(callback):
    arglist = aux.to_list(callback.data, 3)
    cid = callback.message.chat.id
    ret = user.penal_func(arglist)
    if ret[0]:
        message = ret[1]
        bot.delete_message(cid, callback.message.message_id)
        bot.send_message(cid, u'Penalización aplicada')
        bot.send_message(int(arglist[1]), message)
    else:
        bot.delete_message(cid, callback.message.message_id)
        bot.send_message(cid, u'No se puede penalizar a ese jugador porque no tiene ningún tiempo guardado.')


@bot.callback_query_handler(func=lambda callback: aux.is_to_list(callback.data, 2)
                                                  and aux.to_list(callback.data, 2)[0] == 'Cambiar nombre')
def rename(callback):
    cid = callback.message.chat.id
    bot.delete_message(cid, callback.message.message_id)
    compid = int(aux.to_list(callback.data, 2)[1])
    bot.send_message(cid, 'Envia el nuevo nombre(competicion en %s)' % compid, reply_markup=types.ForceReply())


@bot.message_handler(func=lambda message:not(message.reply_to_message is None) and
                                        len(message.reply_to_message.text) > 21 and
                                        message.reply_to_message.text[0:21] == 'Envia el nuevo nombre' and
                                        message.reply_to_message.from_user.id == bot.get_me().id)
def change_name(message):
    compid = message.reply_to_message.text[37:-1]
    new_name = message.text
    adminid = str(message.from_user.id)
    comp.name(adminid, compid, new_name)
    bot.delete_message(message.chat.id, message.reply_to_message.message_id)
    bot.send_message(message.chat.id, 'Nombre cambiado correctamente')

@bot.callback_query_handler(func=lambda callback: aux.is_to_list(callback.data, 2)
                                                  and aux.to_list(callback.data, 2)[0] == 'Eliminar competicion')
def delete(callback):
    compid = aux.to_list(callback.data, 2)[1]
    uid = callback.from_user.id
    cid = callback.message.chat.id
    comp.delete_comp(compid, uid)
    bot.delete_message(cid, callback.message.message_id)
    bot.send_message(cid, 'Competicion eliminada correctamente')


@bot.callback_query_handler(func=lambda callback: True)
def test(callback):
    print(callback.data)


#################Mensajes Especiales#####################
#semaforo -> 🚥
@bot.message_handler(commands=['podium_comp'])
def podium_info(m):
    #-*- coding: utf-8 -*-
    #Este comando nos dará información sobre el podium
    cid = m.chat.id
    rank = rank_func.ranking(cid)
    #copa dorada, plateada para el 2º, etc; medallas para el podio de las carreras, copas para el final
    try:
        sendMarkdownMessage(cid, """
                        🏆 *Pódium del Campeonato* 🏆
                        🏁Enhorabuena a los pilotos🏁


                        _JUGADOR_                       _PUNTOS_
                🥇     *1º Puesto*      🥇
                            {}                              {}

                🥈     *2º Puesto*      🥈
                            {}                              {}

                🥉     *3º Puesto*      🥉
                            {}                              {}

            """.format(rank[0][0],rank[0][1],rank[1][0],rank[1][1],rank[2][0],rank[2][1]))
    except:
        print "ERROR: No se pudo enviar el podium del torneo"
        send_message(m, "No se puede crear el podium")



@bot.message_handler(commands=['rank_comp'])
def clasif_info(m):
    #-*- coding: utf-8 -*-
    #Este comando nos dará información sobre la clasificación del campeonato
    cid = m.chat.id
    rank = rank_func.ranking(cid)
    try:
        cabecera = '''
             🏆 *Clasificación del campeonato* 🏆
                🏁Enhorabuena a los pilotos🏁

        *Posición*      *Nombre*                        *Puntos*
        *1º Puesto*     {}                  🥇              {}
        *2º Puesto*     {}                  🥈              {}
        *3º Puesto*     {}                  🥉              {}'''.format(rank[0][0],rank[0][1],rank[1][0],rank[1][1],rank[2][0],rank[2][1])

        i = 3
        while i < len(rank):
            aux ='''
            *{}º Puesto*     {}                                 {}'''.format((i+1),rank[i][0], rank[i][1])
            cabecera = cabecera + aux
            i += 1

        sendMarkdownMessage(cid, cabecera)
    except:
        print ("ERROR: No se pudo enviar la clasificacion del torneo")
        send_message(m, "No se puede crear la tabla de clasificacion")


@bot.message_handler(commands=['rank_race'])
def lrace_info(m):
    #🏁Enhorabuena a los pilotos🏁
    #-*- coding: utf-8 -*-
    #Este comando nos dará información sobre la clasificación de la ultima carrera

    cid = m.chat.id
    rank = timef.race_ranking(cid)
    try:
        cabecera = '''
             🏆 *Clasificación de la carrera* 🏆
                🏁Enhorabuena a los pilotos🏁

        *Posición*      *Nombre*                        *Tiempo*
        *1º Puesto*     {}                 🥇               {}
        *2º Puesto*     {}                 🥈               {}
        *3º Puesto*     {}                 🥉               {}'''.format(rank[0][0],rank[0][1],rank[1][0],rank[1][1],rank[2][0],rank[2][1])

        i = 3
        while i < len(rank):
            nextp = '''
            *{}º Puesto*     {}                                 {}'''.format((i+1), rank[i][0], rank[i][1])
            cabecera = cabecera + nextp
            i += 1
        sendMarkdownMessage(cid, cabecera)
    except:
        print "ERROR: No se pudo enviar el podium de la carrera"
        send_message(m, "No se puede crear el podium")


bot.polling()
