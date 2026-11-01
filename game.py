from __future__ import annotations

import asyncio
import json
import math
import os
import queue
import random
import re
import base64
import tempfile
import subprocess
import sys
import threading
import time
from array import array
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import aiohttp
import edge_tts
import pygame


WIDTH, HEIGHT = 1600, 900
FPS = 60
NEURAL_VOICES = {
    "it": (
        ("it-IT-IsabellaNeural", "Isabella"),
        ("it-IT-ElsaNeural", "Elsa"),
        ("it-IT-DiegoNeural", "Diego"),
        ("it-IT-GiuseppeMultilingualNeural", "Giuseppe"),
    ),
    "en": (
        ("en-US-AriaNeural", "Aria"),
        ("en-GB-SoniaNeural", "Sonia"),
        ("en-US-GuyNeural", "Guy"),
    ),
}
NEURAL_VOICE_LABELS = {
    voice_id: name
    for voices in NEURAL_VOICES.values()
    for voice_id, name in voices
}
NEURAL_VOICE_IDS = frozenset(NEURAL_VOICE_LABELS)
RESOLUTIONS = [
    (1280, 720),
    (1366, 768),
    (1600, 900),
]
FONT_CACHE: dict[tuple[str, int, bool], pygame.font.Font] = {}
TEXT_CACHE: dict[tuple[str, int, bool, tuple[int, int, int], str], pygame.Surface] = {}
GOLD = (218, 183, 118)
PALE_GOLD = (241, 216, 167)
PARCHMENT = (227, 220, 201)
MUTED = (150, 151, 148)
FONT_BODY = "segoe ui"
FONT_TITLE = "georgia"
SETTINGS_FILE = "settings.json"


def get_font(name: str, size: int, bold: bool = False) -> pygame.font.Font:
    key = (name, size, bold)
    face = FONT_CACHE.get(key)
    if face is None:
        face = pygame.font.SysFont(name, size, bold=bold)
        FONT_CACHE[key] = face
    return face

TEXT = {
    "it": {
        "subtitle": "UNA STORIA FANTASY, SCRITTA INSIEME",
        "tagline": "Il destino non si aspetta. Si affronta.",
        "play": "GIOCA",
        "settings": "IMPOSTAZIONI",
        "quit": "ESCI",
        "footnote": "UN'AVVENTURA ORIGINALE DI DUNGEON & BARD",
        "settings_title": "Impostazioni",
        "display": "SCHERMO",
        "resolution": "Risoluzione",
        "window_mode": "Modalità schermo",
        "windowed": "Finestra",
        "fullscreen": "Schermo intero",
        "language": "Lingua",
        "voice": "Timbro narratore",
        "voice_locale": "Lingua narratore",
        "voice_auto": "Automatica",
        "voice_it": "Italiano",
        "voice_en": "English",
        "voice_recommended": "Consigliata",
        "voice_neural_online": "Neurale · online gratis",
        "voice_system_offline": "voce di Windows",
        "voice_privacy_hint": "La voce naturale gratuita richiede Internet e invia il testo a Microsoft.",
        "voice_cancelling": "ANNULLAMENTO...",
        "audio": "AUDIO",
        "cloud_narrator": "NARRATORE IA",
        "cloud_configure": "IMPOSTA",
        "cloud_offline": "Offline",
        "cloud_ready": "Worker configurato",
        "cloud_title": "Un narratore che improvvisa",
        "cloud_subtitle": "Collega il tuo Worker Cloudflare: il regolamento resta nel gioco, la storia prende vita con l'IA.",
        "cloud_endpoint_label": "URL DEL WORKER",
        "cloud_endpoint_placeholder": "https://nome-worker.nome-account.workers.dev",
        "cloud_token_label": "TOKEN DI ACCESSO",
        "cloud_token_placeholder": "Incolla il token segreto del Worker",
        "cloud_setup_hint": "Distribuisci il Worker nella cartella cloudflare. Incolla qui l'URL e usa Ctrl+V per il token.",
        "cloud_privacy_hint": "Ambientazione, nomi, azioni, tiri e parte della cronologia vengono inviati a Cloudflare. Non inserire dati personali.",
        "cloud_clipboard_error": "Appunti non disponibili. Verifica gli appunti di Windows e riprova.",
        "cloud_endpoint_error": "Inserite un URL HTTPS valido del Worker (HTTP e consentito solo per localhost).",
        "cloud_token_required": "Inserite il token di accesso configurato nel Worker.",
        "cloud_token_invalid": "Token rifiutato dal Worker. Verificate che il token salvato corrisponda al segreto Cloudflare.",
        "cloud_narrating": "Il narratore sta intrecciando la scena...",
        "cloud_unavailable": "Il narratore online non risponde: proseguo con la scena locale.",
        "cloud_rate_limited": "Il narratore e momentaneamente occupato o ha raggiunto il limite. Riprovate tra poco.",
        "cloud_back": "INDIETRO",
        "cloud_apply": "SALVA",
        "master_volume": "Volume generale",
        "music_volume": "Musica",
        "effects_volume": "Effetti sonori",
        "apply": "APPLICA",
        "back": "INDIETRO",
        "saved": "Impostazioni salvate",
        "save_error": "Non è stato possibile salvare le impostazioni.",
        "audio_unavailable": "Audio non disponibile su questo dispositivo.",
        "quit_title": "Vuoi lasciare l'avventura?",
        "quit_hint": "I progressi non salvati andranno persi.",
        "quit_confirm": "SÌ, ESCI",
        "quit_cancel": "CONTINUA A GIOCARE",
        "back_hint": "MODIFICA LE IMPOSTAZIONI CON CALMA. IL MONDO PUÒ ASPETTARE.",
        "settings_unreadable": "Impostazioni illeggibili: sono stati ripristinati i valori predefiniti.",
        "create_title": "La vostra avventura",
        "create_subtitle": "Scegliete il mondo e preparate i personaggi.",
        "step_adventure": "PASSO 1 DI 2 · AVVENTURA",
        "step_characters": "PASSO 2 DI 2 · PERSONAGGI",
        "character_page_title": "Chi parte all'avventura?",
        "character_page_subtitle": "Date un nome a ogni personaggio, scegliete specie e classe, poi distribuite i punti.",
        "character_stats": "CARATTERISTICHE",
        "character_summary": "27 punti da distribuire · valori da 8 a 15",
        "character_health": "Punti ferita iniziali: {hp}",
        "continue_characters": "SCEGLI I PERSONAGGI",
        "back_adventure": "INDIETRO",
        "players_count_one": "1 giocatore",
        "players_count_many": "{count} giocatori",
        "players": "NUMERO DI GIOCATORI",
        "duration": "DURATA DELLA PARTITA",
        "minutes": "minuti",
        "difficulty": "DIFFICOLTÀ",
        "easy": "Facile",
        "easy_desc": "Perfetta per cominciare",
        "medium": "Media",
        "medium_desc": "Una sfida equilibrata",
        "hard": "Difficile",
        "hard_desc": "Per gruppi esperti",
        "setting": "AMBIENTAZIONE NARRATIVA",
        "roll_setting": "Estrai un'ambientazione casuale",
        "setting_placeholder": "Es. un regno avvolto da una nebbia incantata…",
        "characters": "CREA I PERSONAGGI",
        "character_placeholder": "Nome del personaggio",
        "species": "SPECIE",
        "class": "CLASSE",
        "point_buy": "Punti caratteristiche: {points}/27",
        "ability_short": ("FOR", "DES", "COS", "INT", "SAG", "CAR"),
        "proficiency": "Competenza",
        "hit_points": "PF",
        "extra": "AGGIUNTE FACOLTATIVE",
        "extra_placeholder": "Un mistero, un oggetto, un alleato…",
        "start_adventure": "INIZIA L'AVVENTURA",
        "field_required": "Inserite un'ambientazione, date un nome a ogni personaggio e usate tutti i 27 punti.",
        "setting_required": "Prima scegliete o descrivete l'ambientazione.",
        "world_1": "Un villaggio di montagna dove le ombre si muovono da sole.",
        "world_2": "Un regno sotterraneo costruito tra radici gigantesche.",
        "world_3": "Un porto sospeso sopra un mare di nuvole.",
        "world_4": "Una foresta antica in cui ogni sentiero cambia a mezzanotte.",
        "world_5": "Una città di vetro minacciata da un drago addormentato.",
        "world_6": "Un deserto stellato attraversato da carovane scomparse.",
        "adventure": "LA VOSTRA AVVENTURA",
        "narrator": "IL NARRATORE",
        "action_placeholder": "Cosa fa {player}? (oppure passate il turno)",
        "send": "INVIA",
        "narration_wait": "Il narratore valuta la vostra azione...",
        "dice_rolling": "IL DADO ROTOLA",
        "dice_result": "{die} · {result}",
        "damage_roll": "Danni {die}: {result}",
        "dice_check_label": "PROVA",
        "dice_damage_label": "DANNI",
        "turn_count": "AZIONI: {count}",
        "turn_display": "TURNO DI {name} · {duration} min",
        "turn_speaker": "TURNO DI {name}",
        "class_feature": "SPUNTO NARRATIVO DI CLASSE · NON È UN BONUS",
        "local_opening": "La vostra avventura comincia: {setting}.{extra}\n\nPotete guardarvi intorno, parlare con qualcuno o tentare qualsiasi altra cosa: non c'è una scelta obbligata. Da dove cominciate?",
        "local_action": "{actor} agisce: {action}. La scena reagisce e la situazione è cambiata. Cosa fate adesso?",
        "local_check_success": "{actor} riesce: {action}. Il risultato vi apre nuove possibilità, ma la prossima mossa resta vostra. Che cosa fate?",
        "local_check_failure": "{actor} non ottiene ciò che sperava: {action}. L'imprevisto cambia la situazione, senza costringervi a ripetere lo stesso tentativo. Come reagite?",
        "offline_action": "Azione registrata. Senza il narratore online non posso valutarne l'esito: descrivetela in un altro modo oppure collegate il Worker.",
        "offline_check_success": "La prova riesce. Il tentativo ha successo.",
        "offline_check_failure": "La prova fallisce. La situazione cambia, ma la storia continua.",
        "narration_send": "ATTENDI",
        "listen": "ASCOLTA",
        "stop_voice": "FERMA VOCE",
        "mute_voice": "MUTA VOCE",
        "unmute_voice": "RIATTIVA VOCE",
        "voice_generating": "PREPARO LA VOCE...",
        "voice_unavailable": "La voce narrante è disponibile solo su Windows.",
        "voice_error": "Impossibile avviare la voce narrante.",
        "voice_online_error": "Voce naturale non disponibile: controllate Internet o scegliete una voce di Windows.",
        "new_adventure": "NUOVA AVVENTURA",
        "choose_action": "SCELTA DEL GRUPPO",
        "no_action": "Descrivete la prossima mossa del gruppo.",
        "action_required": "Scrivete un'azione in parole, non un numero o una risposta vuota.",
        "check_detail": "{character} ({class_name}) · {ability} {score}: modificatore {modifier}{proficiency} · bonus totale {total_modifier:+d}.",
        "check_roll": "D20: {roll} {modifier} = {total} contro CD {target}.",
        "short_skill": "prova",
        "stat_strength": "Forza",
        "stat_dexterity": "Destrezza",
        "stat_constitution": "Costituzione",
        "stat_intelligence": "Intelligenza",
        "stat_wisdom": "Saggezza",
        "stat_charisma": "Carisma",
        "skill_athletics": "Atletica",
        "skill_acrobatics": "Acrobazia",
        "skill_stealth": "Furtività",
        "skill_sleight": "Rapidità di mano",
        "skill_investigation": "Indagare",
        "skill_arcana": "Arcano",
        "skill_history": "Storia",
        "skill_religion": "Religione",
        "skill_nature": "Natura",
        "skill_perception": "Percezione",
        "skill_survival": "Sopravvivenza",
        "skill_insight": "Intuizione",
        "skill_medicine": "Medicina",
        "skill_animal": "Addestrare animali",
        "skill_persuasion": "Persuasione",
        "skill_deception": "Inganno",
        "skill_intimidation": "Intimidire",
        "skill_performance": "Intrattenimento",
        "species_human": "Umano",
        "species_elf": "Elfo",
        "species_dwarf": "Nano",
        "species_halfling": "Halfling",
        "species_gnome": "Gnomo",
        "species_dragonborn": "Dragonide",
        "species_tiefling": "Tiefling",
        "species_orc": "Orco",
        "species_goliath": "Goliath",
        "species_aasimar": "Aasimar",
        "class_barbarian": "Barbaro",
        "class_bard": "Bardo",
        "class_cleric": "Chierico",
        "class_druid": "Druido",
        "class_fighter": "Guerriero",
        "class_monk": "Monaco",
        "class_paladin": "Paladino",
        "class_ranger": "Ranger",
        "class_rogue": "Ladro",
        "class_sorcerer": "Stregone",
        "class_warlock": "Warlock",
        "class_wizard": "Mago",
        "character_number": "PERSONAGGIO {number}",
        "random_world_hint": "D6: combina luogo, mistero e minaccia",
        "hint_create": "IL NARRATORE COSTRUIRÀ LA STORIA SULLE VOSTRE SCELTE",
        "hero_one": "1 personaggio",
        "hero_many": "{count} personaggi",
    },
    "en": {
        "subtitle": "A FANTASY STORY, WRITTEN TOGETHER",
        "tagline": "Destiny won't wait. Face it.",
        "play": "PLAY",
        "settings": "SETTINGS",
        "quit": "QUIT",
        "footnote": "AN ORIGINAL DUNGEON & BARD ADVENTURE",
        "settings_title": "Settings",
        "display": "DISPLAY",
        "resolution": "Resolution",
        "window_mode": "Display mode",
        "windowed": "Windowed",
        "fullscreen": "Fullscreen",
        "language": "Language",
        "voice": "Narrator voice",
        "voice_locale": "Narrator language",
        "voice_auto": "Automatic",
        "voice_it": "Italian",
        "voice_en": "English",
        "voice_recommended": "Recommended",
        "voice_neural_online": "Neural · free online",
        "voice_system_offline": "Windows voice",
        "voice_privacy_hint": "Free natural speech needs Internet and sends the text to Microsoft.",
        "voice_cancelling": "CANCELLING...",
        "audio": "AUDIO",
        "cloud_narrator": "AI NARRATOR",
        "cloud_configure": "SET UP",
        "cloud_offline": "Offline",
        "cloud_ready": "Worker configured",
        "cloud_title": "A narrator who can improvise",
        "cloud_subtitle": "Connect your Cloudflare Worker: game rules stay local while AI brings the story to life.",
        "cloud_endpoint_label": "WORKER URL",
        "cloud_endpoint_placeholder": "https://worker-name.account-name.workers.dev",
        "cloud_token_label": "ACCESS TOKEN",
        "cloud_token_placeholder": "Paste the Worker secret token",
        "cloud_setup_hint": "Deploy the Worker in the cloudflare folder. Paste its URL here; use Ctrl+V for the token.",
        "cloud_privacy_hint": "Setting, names, actions, rolls, and some history are sent to Cloudflare. Do not enter personal data.",
        "cloud_clipboard_error": "Clipboard is unavailable. Check your Windows clipboard and try again.",
        "cloud_endpoint_error": "Enter a valid HTTPS Worker URL (HTTP is only allowed for localhost).",
        "cloud_token_required": "Enter the access token configured in the Worker.",
        "cloud_token_invalid": "The Worker rejected the token. Check that the saved token matches the Cloudflare secret.",
        "cloud_narrating": "The narrator is weaving the scene...",
        "cloud_unavailable": "The online narrator is unavailable; continuing with the local scene.",
        "cloud_rate_limited": "The narrator is busy or has reached its limit. Try again shortly.",
        "cloud_back": "BACK",
        "cloud_apply": "SAVE",
        "master_volume": "Master volume",
        "music_volume": "Music",
        "effects_volume": "Sound effects",
        "apply": "APPLY",
        "back": "BACK",
        "saved": "Settings saved",
        "save_error": "Could not save your settings.",
        "audio_unavailable": "Audio is unavailable on this device.",
        "quit_title": "Leave the adventure?",
        "quit_hint": "Unsaved progress will be lost.",
        "quit_confirm": "YES, QUIT",
        "quit_cancel": "KEEP PLAYING",
        "back_hint": "TAKE YOUR TIME WITH THE SETTINGS. THE WORLD CAN WAIT.",
        "settings_unreadable": "Settings could not be read; default values are in use.",
        "create_title": "Your adventure",
        "create_subtitle": "Choose the world and get your characters ready.",
        "step_adventure": "STEP 1 OF 2 · ADVENTURE",
        "step_characters": "STEP 2 OF 2 · CHARACTERS",
        "character_page_title": "Who is setting out?",
        "character_page_subtitle": "Name each character, choose a species and class, then spend your points.",
        "character_stats": "ABILITIES",
        "character_summary": "27 points to spend · scores from 8 to 15",
        "character_health": "Starting hit points: {hp}",
        "continue_characters": "CHOOSE CHARACTERS",
        "back_adventure": "BACK",
        "players_count_one": "1 player",
        "players_count_many": "{count} players",
        "players": "NUMBER OF PLAYERS",
        "duration": "GAME LENGTH",
        "minutes": "minutes",
        "difficulty": "DIFFICULTY",
        "easy": "Easy",
        "easy_desc": "Perfect for beginners",
        "medium": "Medium",
        "medium_desc": "A balanced challenge",
        "hard": "Hard",
        "hard_desc": "For seasoned parties",
        "setting": "STORY SETTING",
        "roll_setting": "Roll a random setting",
        "setting_placeholder": "e.g. a kingdom shrouded in enchanted mist…",
        "characters": "CREATE YOUR CHARACTERS",
        "character_placeholder": "Character name",
        "species": "SPECIES",
        "class": "CLASS",
        "point_buy": "Ability points: {points}/27",
        "ability_short": ("STR", "DEX", "CON", "INT", "WIS", "CHA"),
        "proficiency": "Proficiency",
        "hit_points": "HP",
        "extra": "OPTIONAL ADDITIONS",
        "extra_placeholder": "A mystery, an item, an ally…",
        "start_adventure": "BEGIN ADVENTURE",
        "field_required": "Enter a setting, name each character, and spend all 27 points.",
        "setting_required": "Choose or describe a story setting first.",
        "world_1": "A mountain village where shadows move on their own.",
        "world_2": "An underground kingdom woven through giant roots.",
        "world_3": "A harbor suspended above a sea of clouds.",
        "world_4": "An ancient forest where every path shifts at midnight.",
        "world_5": "A glass city threatened by a sleeping dragon.",
        "world_6": "A starlit desert crossed by vanished caravans.",
        "adventure": "YOUR ADVENTURE",
        "narrator": "THE NARRATOR",
        "action_placeholder": "What does {player} do? (or pass the turn)",
        "send": "SEND",
        "narration_wait": "The narrator is considering your action...",
        "dice_rolling": "THE DIE IS ROLLING",
        "dice_result": "{die} · {result}",
        "damage_roll": "Damage {die}: {result}",
        "dice_check_label": "CHECK",
        "dice_damage_label": "DAMAGE",
        "turn_count": "ACTIONS: {count}",
        "turn_display": "TURN: {name} · {duration} min",
        "turn_speaker": "{name}'S TURN",
        "class_feature": "CLASS STORY PROMPT · NO ROLL BONUS",
        "local_opening": "Your adventure begins: {setting}.{extra}\n\nYou can look around, speak to someone, or try anything else: there is no required choice. Where do you begin?",
        "local_action": "{actor} acts: {action}. The scene responds, and the situation has changed. What do you do now?",
        "local_check_success": "{actor} succeeds: {action}. The result opens new possibilities, but the next move is yours. What do you do?",
        "local_check_failure": "{actor} does not get what they hoped for: {action}. Something changes, without forcing you to repeat the same attempt. How do you respond?",
        "offline_action": "Action recorded. Without the online narrator I can't judge its outcome; describe it another way or connect the Worker.",
        "offline_check_success": "The check succeeds. The attempted action works.",
        "offline_check_failure": "The check fails. The situation changes, but the story continues.",
        "narration_send": "WAIT",
        "listen": "LISTEN",
        "stop_voice": "STOP VOICE",
        "mute_voice": "MUTE VOICE",
        "unmute_voice": "UNMUTE VOICE",
        "voice_generating": "PREPARING VOICE...",
        "voice_unavailable": "Narration is only available on Windows.",
        "voice_error": "Unable to start the narrator.",
        "voice_online_error": "Natural voice is unavailable: check your connection or choose a Windows voice.",
        "new_adventure": "NEW ADVENTURE",
        "choose_action": "PARTY ACTION",
        "no_action": "Describe your party's next move.",
        "action_required": "Describe an action in words, not a number or an empty reply.",
        "check_detail": "{character} ({class_name}) · {ability} {score}: modifier {modifier}{proficiency} · total bonus {total_modifier:+d}.",
        "check_roll": "D20: {roll} {modifier} = {total} against DC {target}.",
        "short_skill": "check",
        "stat_strength": "Strength",
        "stat_dexterity": "Dexterity",
        "stat_constitution": "Constitution",
        "stat_intelligence": "Intelligence",
        "stat_wisdom": "Wisdom",
        "stat_charisma": "Charisma",
        "skill_athletics": "Athletics",
        "skill_acrobatics": "Acrobatics",
        "skill_stealth": "Stealth",
        "skill_sleight": "Sleight of Hand",
        "skill_investigation": "Investigation",
        "skill_arcana": "Arcana",
        "skill_history": "History",
        "skill_religion": "Religion",
        "skill_nature": "Nature",
        "skill_perception": "Perception",
        "skill_survival": "Survival",
        "skill_insight": "Insight",
        "skill_medicine": "Medicine",
        "skill_animal": "Animal Handling",
        "skill_persuasion": "Persuasion",
        "skill_deception": "Deception",
        "skill_intimidation": "Intimidation",
        "skill_performance": "Performance",
        "species_human": "Human",
        "species_elf": "Elf",
        "species_dwarf": "Dwarf",
        "species_halfling": "Halfling",
        "species_gnome": "Gnome",
        "species_dragonborn": "Dragonborn",
        "species_tiefling": "Tiefling",
        "species_orc": "Orc",
        "species_goliath": "Goliath",
        "species_aasimar": "Aasimar",
        "class_barbarian": "Barbarian",
        "class_bard": "Bard",
        "class_cleric": "Cleric",
        "class_druid": "Druid",
        "class_fighter": "Fighter",
        "class_monk": "Monk",
        "class_paladin": "Paladin",
        "class_ranger": "Ranger",
        "class_rogue": "Rogue",
        "class_sorcerer": "Sorcerer",
        "class_warlock": "Warlock",
        "class_wizard": "Wizard",
        "character_number": "CHARACTER {number}",
        "random_world_hint": "D6: combine a place, mystery, and threat",
        "hint_create": "THE NARRATOR WILL BUILD THE STORY AROUND YOUR CHOICES",
        "hero_one": "1 character",
        "hero_many": "{count} characters",
    },
}

ABILITY_KEYS = ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma")
ABILITY_ABBREVIATIONS = ("str", "dex", "con", "int", "wis", "cha")
POINT_BUY_COST = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
SPECIES_KEYS = (
    "human", "elf", "dwarf", "halfling", "gnome", "dragonborn", "tiefling", "orc", "goliath", "aasimar",
)
CLASS_KEYS = (
    "barbarian", "bard", "cleric", "druid", "fighter", "monk",
    "paladin", "ranger", "rogue", "sorcerer", "warlock", "wizard",
)
CLASS_DATA = {
    "barbarian": {"primary": "strength", "saves": ("strength", "constitution"), "hit_die": 12, "skills": ("athletics", "intimidation")},
    "bard": {"primary": "charisma", "saves": ("dexterity", "charisma"), "hit_die": 8, "skills": ("performance", "persuasion")},
    "cleric": {"primary": "wisdom", "saves": ("wisdom", "charisma"), "hit_die": 8, "skills": ("insight", "religion")},
    "druid": {"primary": "wisdom", "saves": ("intelligence", "wisdom"), "hit_die": 8, "skills": ("nature", "survival")},
    "fighter": {"primary": "strength", "saves": ("strength", "constitution"), "hit_die": 10, "skills": ("athletics", "perception")},
    "monk": {"primary": "dexterity", "saves": ("strength", "dexterity"), "hit_die": 8, "skills": ("acrobatics", "insight")},
    "paladin": {"primary": "strength", "saves": ("wisdom", "charisma"), "hit_die": 10, "skills": ("athletics", "persuasion")},
    "ranger": {"primary": "dexterity", "saves": ("strength", "dexterity"), "hit_die": 10, "skills": ("perception", "survival")},
    "rogue": {"primary": "dexterity", "saves": ("dexterity", "intelligence"), "hit_die": 8, "skills": ("stealth", "sleight")},
    "sorcerer": {"primary": "charisma", "saves": ("constitution", "charisma"), "hit_die": 6, "skills": ("arcana", "deception")},
    "warlock": {"primary": "charisma", "saves": ("wisdom", "charisma"), "hit_die": 8, "skills": ("arcana", "intimidation")},
    "wizard": {"primary": "intelligence", "saves": ("intelligence", "wisdom"), "hit_die": 6, "skills": ("arcana", "investigation")},
}
CLASS_STORY_FEATURES = {
    "barbarian": {
        "it": ("Istinto primordiale", "Capisce quando serve la forza o come incutere timore."),
        "en": ("Primal instinct", "Knows when to use strength or strike fear."),
    },
    "bard": {
        "it": ("Ispirazione", "Usa parole e musica per coinvolgere, incoraggiare o convincere."),
        "en": ("Inspiration", "Uses words and music to engage, encourage, or persuade."),
    },
    "cleric": {
        "it": ("Rimedio sacro", "Riconosce presenze sacre e legge le intenzioni altrui."),
        "en": ("Sacred insight", "Recognizes sacred presences and reads others' intentions."),
    },
    "druid": {
        "it": ("Voce del vivente", "Interpreta tracce, piante e comportamenti animali."),
        "en": ("Voice of the wild", "Reads tracks, plants, and animal behavior."),
    },
    "fighter": {
        "it": ("Tattica marziale", "Individua varchi e protegge chi gli sta accanto."),
        "en": ("Battle tactics", "Spots openings and protects nearby allies."),
    },
    "monk": {
        "it": ("Movimento fluido", "Supera ostacoli con agilità e legge i movimenti altrui."),
        "en": ("Flowing movement", "Crosses obstacles nimbly and reads others' movements."),
    },
    "paladin": {
        "it": ("Presenza salda", "Dà coraggio e convince con la forza dei suoi giuramenti."),
        "en": ("Steadfast presence", "Bolsters courage and persuades through steadfast vows."),
    },
    "ranger": {
        "it": ("Occhio della selva", "Legge piste e orienta il gruppo in territori ostili."),
        "en": ("Wildsight", "Reads tracks and guides the party through hostile terrain."),
    },
    "rogue": {
        "it": ("Mani esperte", "Nota dettagli nascosti e agisce con precisione."),
        "en": ("Expert hands", "Spots hidden details and acts with precision."),
    },
    "sorcerer": {
        "it": ("Scintilla innata", "Modella la magia e confonde gli avversari con istinto."),
        "en": ("Innate spark", "Shapes magic and misdirects foes through instinct."),
    },
    "warlock": {
        "it": ("Patto arcano", "Riconosce segni occulti e impone rispetto con il suo patto."),
        "en": ("Arcane pact", "Recognizes occult signs and commands respect through the pact."),
    },
    "wizard": {
        "it": ("Sapere arcano", "Decifra fenomeni magici e indizi con metodo."),
        "en": ("Arcane study", "Deciphers magical phenomena and clues methodically."),
    },
}
SKILL_ABILITIES = {
    "athletics": "strength",
    "acrobatics": "dexterity",
    "stealth": "dexterity",
    "sleight": "dexterity",
    "investigation": "intelligence",
    "arcana": "intelligence",
    "history": "intelligence",
    "religion": "intelligence",
    "nature": "intelligence",
    "perception": "wisdom",
    "survival": "wisdom",
    "insight": "wisdom",
    "medicine": "wisdom",
    "animal": "wisdom",
    "persuasion": "charisma",
    "deception": "charisma",
    "intimidation": "charisma",
    "performance": "charisma",
}
ACTION_KEYWORDS = (
    ("attack", ("attacc", "combatt", "colp", "ferisc", "sconfigg", "uccid", "spada", "frecc", "arco", "attack", "fight", "strike", "sword", "arrow", "shoot")),
    ("spellcasting", ("incantesim", "lancio un incantesimo", "lanciamo un incantesimo", "uso magia", "uso un incantesimo", "magia", "cast a spell", "cast spell", "cast magic", "spell")),
    ("athletics", ("sollev", "forz", "romp", "sping", "trascin", "abbatt", "scal", "arrampic", "sfond", "apri", "muovo il masso", "lift", "force", "break", "push", "drag", "climb", "open the door", "open the gate", "athlet")),
    ("acrobatics", ("schiv", "equilibr", "capriol", "salto", "saltare", "agil", "attraverso il ponte", "dodge", "balance", "leap", "jump", "acrobat")),
    ("stealth", ("furtiv", "nascond", "silenz", "infiltr", "sgattaiol", "sneak", "hide", "quietly", "stealth")),
    ("sleight", ("bors", "tasca", "scassin", "grimald", "rub", "pickpocket", "lockpick", "sleight")),
    ("investigation", ("indag", "cerc", "esamin", "ispezion", "analizz", "perquis", "studia", "investig", "search", "inspect", "examine", "investigate", "study")),
    ("arcana", ("decifr", "runa", "sigill", "arcano", "sortilegio", "rune", "seal", "decipher", "decode", "arcana")),
    ("history", ("storia", "storico", "cronaca", "history", "historical")),
    ("religion", ("religion", "divinit", "sacro", "sacred", "deity", "temple")),
    ("nature", ("natura", "pianta", "fungo", "animale selvatico", "plant", "fungus", "wildlife", "nature")),
    ("perception", ("osserv", "ascolt", "notar", "scrut", "guard", "percep", "listen", "spot", "watch", "notice", "look around", "terrain", "terreno")),
    ("survival", ("tracci", "seguo le tracce", "orient", "sopravviv", "pista", "cacci", "seguo il sentiero", "track", "navigate", "survive", "hunt")),
    ("insight", ("intu", "intenzion", "capisco se", "leggo il volto", "leggo le sue", "read their", "read his", "read her", "insight")),
    ("medicine", ("cur", "guar", "medic", "stabilizz", "bend", "heal", "treat the wound", "medicine")),
    ("animal", ("cavalc", "calm", "addestr", "dom", "caval", "animali", "animal handling", "handle the animal")),
    ("persuasion", ("convinc", "persuad", "negozi", "chied", "implor", "negozi", "persuad", "parl", "convince", "persuade", "persuasion", "negotiate", "ask them", "talk to", "discuss")),
    ("deception", ("ment", "ingann", "fing", "imbrogli", "decep", "lie", "deceive", "trick", "pretend")),
    ("intimidation", ("intimid", "minacci", "spavento", "terroriz", "minacc", "threaten", "scare", "intimidate")),
    ("performance", ("recit", "canto", "suono", "distraggo con uno spettacolo", "esib", "perform", "sing", "play music", "entertain")),
)
WORLD_TABLES = {
    "it": {
        "places": (
            "un arcipelago sospeso sopra un mare di nubi", "una metropoli costruita dentro un colossale albero pietrificato",
            "una città in rovina inghiottita dal ghiaccio", "un monastero scavato nel fianco di un vulcano dormiente",
            "una frontiera dove il sole non tramonta mai", "una biblioteca sotterranea grande quanto un regno",
            "un faro isolato sulle rive di un oceano senza stelle", "una valle in cui convivono villaggi di epoche diverse",
            "un deserto attraversato da fiumi che scorrono nel cielo", "una fortezza abbandonata al confine del mondo",
            "una città di vetro sorta attorno a un cratere luminoso", "una foresta le cui radici attraversano dimensioni",
            "una rete di caverne illuminate da funghi giganti", "un regno costruito sul dorso di creature addormentate",
            "un porto franco dove attraccano navi fantasma", "una distesa di pianure ricoperte da statue colossali",
            "un villaggio di montagna tagliato fuori dalle valanghe", "un quartiere sommerso raggiungibile solo con la bassa marea",
        ),
        "wonders": (
            "le ombre si muovono con un istante di anticipo", "ogni campana suona una lingua diversa",
            "la pioggia cade verso l'alto", "i ricordi delle persone appaiono come lucciole",
            "la magia lascia impronte visibili sulla pietra", "le stelle cambiano posizione quando qualcuno mente",
            "le porte si aprono soltanto per chi racconta un segreto", "la notte dura un'ora in più a ogni luna nuova",
            "le statue sussurrano i nomi dei visitatori", "i sogni diventano reali per pochi minuti all'alba",
            "le mappe si aggiornano da sole, ma omettono un luogo", "ogni specchio mostra una stagione differente",
            "le parole dimenticate riaffiorano nell'acqua", "i sentieri conducono dove il viaggiatore ha più paura",
            "una musica lontana cambia il tempo atmosferico", "le candele si accendono vicino ai fantasmi",
            "le impronte indicano il futuro anziché il passato", "la gravità cambia durante le eclissi",
        ),
        "threats": (
            "una gilda di cartografi è scomparsa durante il solstizio", "un patto antico sta per essere infranto",
            "qualcuno vende ricordi rubati al mercato nero", "una creatura imita le voci delle persone amate",
            "il fiume ha iniziato a restituire oggetti mai perduti", "una corona senza sovrano sceglie i propri portatori",
            "un'eclissi sta cancellando lentamente i confini della regione", "una spedizione è tornata senza le proprie ombre",
            "una maschera permette di cambiare volto, ma non di toglierla", "una campana suonerà quando il villaggio scomparirà",
            "un drago addormentato sogna la distruzione del regno", "due casate si contendono un erede che non esiste",
            "una lettera arriva ogni giorno dal futuro con una nuova minaccia", "gli abitanti stanno dimenticando il proprio nome",
            "un'antica strada riappare e chi la percorre invecchia al contrario", "un falso alleato sta preparando un colpo di stato",
            "qualcosa risponde alle richieste d'aiuto dal pozzo sigillato", "una pioggia di cenere annuncia il ritorno di un esiliato",
        ),
    },
    "en": {
        "places": (
            "a chain of islands suspended above a sea of clouds", "a city built inside a colossal petrified tree",
            "the ruins of a settlement swallowed by ice", "a monastery carved into a sleeping volcano",
            "a frontier where the sun never sets", "an underground library as vast as a kingdom",
            "a lonely lighthouse on a starless ocean", "a valley where villages from different ages coexist",
            "a desert crossed by rivers flowing through the sky", "an abandoned fortress at the edge of the world",
            "a glass city built around a glowing crater", "a forest whose roots cross between dimensions",
            "a cavern network lit by enormous mushrooms", "a kingdom built upon sleeping creatures",
            "a free port where ghost ships come to dock", "a plain covered in colossal statues",
            "a mountain village cut off by avalanches", "a drowned district reached only at low tide",
        ),
        "wonders": (
            "shadows move a heartbeat before their owners", "every bell rings in a different language",
            "rain falls upward", "people's memories appear as fireflies",
            "magic leaves visible footprints on stone", "the stars shift whenever someone lies",
            "doors open only for those who share a secret", "each new moon makes the night an hour longer",
            "statues whisper the names of visitors", "dreams become real for a few minutes at dawn",
            "maps update themselves but leave one place out", "every mirror shows a different season",
            "forgotten words surface in water", "paths lead where travellers are most afraid to go",
            "distant music changes the weather", "candles ignite near ghosts",
            "footprints point to the future instead of the past", "gravity shifts during eclipses",
        ),
        "threats": (
            "a guild of mapmakers vanished on the solstice", "an ancient pact is about to be broken",
            "someone is selling stolen memories on the black market", "a creature is mimicking the voices of loved ones",
            "the river has begun returning objects that were never lost", "a crown without a ruler is choosing its bearers",
            "an eclipse is slowly erasing the region's borders", "an expedition returned without its shadows",
            "a mask changes its wearer's face but cannot be removed", "a bell will ring when the village disappears",
            "a sleeping dragon dreams of the kingdom's destruction", "two houses are fighting over an heir who does not exist",
            "a letter from the future arrives each day with a new threat", "the inhabitants are forgetting their own names",
            "an ancient road has returned, and travellers age backwards upon it", "a false ally is planning a coup",
            "something answers calls for help from the sealed well", "a rain of ash heralds an exile's return",
        ),
    },
}


def ability_modifier(score: int) -> int:
    return (score - 10) // 2


def point_buy_total(abilities: dict[str, int]) -> int:
    return sum(POINT_BUY_COST[score] for score in abilities.values())


def initial_abilities(class_key: str) -> dict[str, int]:
    primary = CLASS_DATA[class_key]["primary"]
    priorities = (primary, "constitution", "dexterity", "wisdom", "intelligence", "charisma", "strength")
    ordered = list(dict.fromkeys(priorities))
    for ability in ABILITY_KEYS:
        if ability not in ordered:
            ordered.append(ability)
    values = (15, 14, 13, 12, 10, 8)
    return dict(zip(ordered, values))


def generate_random_setting(language: str) -> str:
    table = WORLD_TABLES[language]
    if language == "it":
        return (
            f"Nel cuore di {random.choice(table['places'])}, {random.choice(table['wonders'])}; "
            f"intanto, {random.choice(table['threats'])}."
        )
    return (
        f"In the heart of {random.choice(table['places'])}, {random.choice(table['wonders'])}; "
        f"meanwhile, {random.choice(table['threats'])}."
    )


def analyze_action(value: str) -> str | None:
    normalized = value.casefold()
    for skill, keywords in ACTION_KEYWORDS:
        if any(
            re.search(r"(?<!\w)arco(?!\w)", normalized)
            if keyword == "arco"
            else keyword in normalized
            for keyword in keywords
        ):
            return skill
    return None


def settings_path() -> Path:
    root = os.environ.get("LOCALAPPDATA")
    base = Path(root) if root else Path.home() / ".local" / "share"
    return base / "DungeonAndBard" / SETTINGS_FILE


def valid_narrator_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        is_local = hostname in ("localhost", "127.0.0.1", "::1")
        return (
            parsed.scheme in ("https", "http")
            and hostname is not None
            and (parsed.scheme == "https" or is_local)
            and parsed.username is None
            and parsed.password is None
            and not parsed.query
            and not parsed.fragment
        )
    except ValueError:
        return False


def default_settings() -> dict:
    return {
        "resolution": [1600, 900],
        "fullscreen": False,
        "language": "it",
        "voice_locale": "auto",
        "voice_name": "",
        "narrator_url": "",
        "narrator_token": "",
        "master": 0.8,
        "music": 0.35,
        "effects": 0.7,
    }


def load_settings() -> tuple[dict, str | None]:
    path = settings_path()
    if not path.exists():
        return default_settings(), None
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_settings(), "settings_unreadable"
    defaults = default_settings()
    if not isinstance(stored, dict):
        return defaults, "settings_unreadable"
    resolution = stored.get("resolution")
    resolution_is_valid = False
    if isinstance(resolution, list) and len(resolution) == 2:
        candidate = tuple(resolution)
        if candidate in RESOLUTIONS:
            defaults["resolution"] = list(candidate)
            resolution_is_valid = True
    if resolution_is_valid and isinstance(stored.get("fullscreen"), bool):
        defaults["fullscreen"] = stored["fullscreen"]
    if stored.get("language") in TEXT:
        defaults["language"] = stored["language"]
    if stored.get("voice_locale") in ("auto", "it", "en"):
        defaults["voice_locale"] = stored["voice_locale"]
    if isinstance(stored.get("voice_name"), str):
        defaults["voice_name"] = stored["voice_name"][:100]
    narrator_url = stored.get("narrator_url")
    if isinstance(narrator_url, str) and len(narrator_url) <= 300:
        narrator_url = narrator_url.strip().rstrip("/")
        if not narrator_url or valid_narrator_url(narrator_url):
            defaults["narrator_url"] = narrator_url
    narrator_token = stored.get("narrator_token")
    if isinstance(narrator_token, str) and len(narrator_token) <= 256:
        defaults["narrator_token"] = narrator_token
    for key in ("master", "music", "effects"):
        value = stored.get(key)
        if isinstance(value, (int, float)) and 0 <= value <= 1:
            defaults[key] = float(value)
    return defaults, None


def save_settings(settings: dict) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    temporary.replace(path)


def make_sound(frequencies: tuple[float, ...], duration: float, volume: float = 0.15) -> pygame.mixer.Sound:
    sample_rate = 22050
    count = int(sample_rate * duration)
    frames = array("h")
    for index in range(count):
        time_value = index / sample_rate
        envelope = min(1.0, index / (sample_rate * 0.02)) * min(1.0, (count - index) / (sample_rate * 0.06))
        value = sum(math.sin(2 * math.pi * frequency * time_value) for frequency in frequencies)
        value = int(32767 * volume * envelope * value / len(frequencies))
        frames.extend((value, value))
    return pygame.mixer.Sound(buffer=frames.tobytes())


def make_ambient_music(
    chords: tuple[tuple[float, ...], ...],
    melody: tuple[float, ...],
    duration: float = 12.0,
) -> pygame.mixer.Sound:
    sample_rate = 22050
    chord_seconds = duration / len(chords)
    sample_count = round(sample_rate * duration)
    frames = array("h")
    rng = random.Random(43)
    wind = 0.0
    wind_target = 0.0

    for index in range(sample_count):
        time_value = index / sample_rate
        chord_index = min(len(chords) - 1, int(time_value / chord_seconds))
        chord_time = time_value - chord_index * chord_seconds
        chord = chords[chord_index]
        pad = sum(
            math.sin(2 * math.pi * frequency * time_value + tone * 0.13)
            for tone, frequency in enumerate(chord)
        ) / len(chord)
        pad *= 0.078 * (0.85 + 0.15 * math.sin(2 * math.pi * chord_time / chord_seconds))
        bass = math.sin(2 * math.pi * chord[0] * 0.5 * time_value) * 0.054

        melody_slot = int(time_value / 1.5)
        note_start = melody_slot * round(sample_rate * 1.5)
        note_time = (index - note_start) / sample_rate
        note = melody[melody_slot % len(melody)]
        bell_wave = (
            math.sin(2 * math.pi * note * note_time)
            + 0.28 * math.sin(2 * math.pi * note * 2.01 * note_time)
            + 0.08 * math.sin(2 * math.pi * note * 3 * note_time)
        )
        bell = bell_wave * math.exp(-note_time * 2.8) * 0.052

        if index % 330 == 0:
            wind_target = rng.uniform(-0.012, 0.012)
        wind += (wind_target - wind) * 0.025
        edge = min(1.0, index / (sample_rate * 0.08), (sample_count - index) / (sample_rate * 0.08))
        sample = max(-1.0, min(1.0, (pad + bass + bell + wind) * edge))
        value = int(sample * 32767)
        frames.extend((value, value))

    return pygame.mixer.Sound(buffer=frames.tobytes())


def make_dice_sound(duration: float = 0.28) -> pygame.mixer.Sound:
    sample_rate = 22050
    count = round(sample_rate * duration)
    frames = array("h")
    rng = random.Random(91)
    filtered_noise = 0.0
    for index in range(count):
        filtered_noise += (rng.uniform(-1.0, 1.0) - filtered_noise) * 0.16
        progress = index / count
        envelope = math.sin(math.pi * progress) * (1.0 - progress * 0.5)
        rattle = filtered_noise * envelope * 0.32
        click = math.sin(2 * math.pi * (390 + 520 * progress) * index / sample_rate)
        click *= max(0.0, 1.0 - progress * 12) * 0.18
        value = int(max(-1.0, min(1.0, rattle + click)) * 32767)
        frames.extend((value, value))
    return pygame.mixer.Sound(buffer=frames.tobytes())


def installed_system_voices() -> list[dict[str, str]]:
    if sys.platform != "win32":
        return []
    script = (
        "Add-Type -AssemblyName System.Speech; "
        "$voices = @((New-Object System.Speech.Synthesis.SpeechSynthesizer)"
        ".GetInstalledVoices() | ForEach-Object { "
        "[PSCustomObject]@{ name = $_.VoiceInfo.Name; locale = "
        "$_.VoiceInfo.Culture.TwoLetterISOLanguageName } }); "
        "ConvertTo-Json -Compress -InputObject $voices"
    )
    command = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-WindowStyle",
                "Hidden",
                "-EncodedCommand",
                command,
            ],
            capture_output=True,
            check=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        raw_voices = json.loads(result.stdout.lstrip("\ufeff").strip() or "[]")
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return []
    if isinstance(raw_voices, dict):
        raw_voices = [raw_voices]
    if not isinstance(raw_voices, list):
        return []
    return [
        {"name": voice["name"], "locale": voice["locale"]}
        for voice in raw_voices
        if isinstance(voice, dict)
        and isinstance(voice.get("name"), str)
        and isinstance(voice.get("locale"), str)
    ]


def voice_preference(voice: dict[str, str]) -> tuple[int, str]:
    name = voice["name"].casefold()
    score = 0
    if "neural" in name or "natural" in name:
        score += 100
    if any(token in name for token in ("aria", "jenny", "zira", "elsa", "lucia", "sara", "hazel")):
        score += 20
    return score, name


def draw_text(
    surface: pygame.Surface,
    value: str,
    position: tuple[int, int],
    size: int = 18,
    colour: tuple[int, int, int] = PARCHMENT,
    *,
    font: str = FONT_BODY,
    centered: bool = False,
    bold: bool = False,
) -> pygame.Rect:
    key = (font, size, bold, colour, value)
    image = TEXT_CACHE.get(key)
    if image is None:
        image = get_font(font, size, bold).render(value, True, colour)
        if len(TEXT_CACHE) >= 1024:
            TEXT_CACHE.pop(next(iter(TEXT_CACHE)))
        TEXT_CACHE[key] = image
    rect = image.get_rect()
    rect.center = position if centered else rect.center
    if not centered:
        rect.topleft = position
    surface.blit(image, rect)
    return rect


def draw_lines(
    surface: pygame.Surface,
    values: list[str],
    position: tuple[int, int],
    size: int,
    colour: tuple[int, int, int],
    gap: int = 29,
) -> None:
    for index, value in enumerate(values):
        draw_text(surface, value, (position[0], position[1] + index * gap), size, colour)


def outlined_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    fill: tuple[int, int, int] = (13, 16, 17),
    border: tuple[int, int, int] = (117, 98, 68),
) -> None:
    pygame.draw.rect(surface, fill, rect, border_radius=5)
    pygame.draw.rect(surface, border, rect, width=1, border_radius=5)
    pygame.draw.line(surface, (201, 168, 102), (rect.x + 17, rect.y + 1), (rect.right - 17, rect.y + 1))


def draw_dragon_mandolin(surface: pygame.Surface, center: tuple[int, int], scale: float = 1.0) -> None:
    cx, cy = center

    def point(x: float, y: float) -> tuple[int, int]:
        return round(cx + x * scale), round(cy + y * scale)

    body = (135, 105, 65)
    edge = GOLD
    pygame.draw.ellipse(surface, body, (*point(-24, -4), round(48 * scale), round(63 * scale)))
    pygame.draw.ellipse(surface, edge, (*point(-24, -4), round(48 * scale), round(63 * scale)), max(1, round(2 * scale)))
    pygame.draw.ellipse(surface, (36, 36, 31), (*point(-14, 14), round(28 * scale), round(24 * scale)))
    pygame.draw.ellipse(surface, PALE_GOLD, (*point(-8, 21), round(16 * scale), round(7 * scale)), max(1, round(scale)))

    neck = [point(-11, 6), point(-7, -27), point(-4, -61), point(0, -70), point(4, -59), point(7, -28), point(11, 7)]
    pygame.draw.polygon(surface, body, neck)
    pygame.draw.lines(surface, edge, True, neck, max(1, round(2 * scale)))
    for y in (-37, -47, -56):
        pygame.draw.line(surface, PALE_GOLD, point(-6, y), point(6, y), max(1, round(scale)))
    for y in (-36, -47, -58):
        direction = -1 if y == -47 else 1
        pygame.draw.circle(surface, edge, point(direction * 8, y - 2), max(2, round(3 * scale)))
        pygame.draw.line(surface, edge, point(direction * 6, y - 2), point(direction * 12, y - 5), max(1, round(scale)))

    head = [(-12, -67), (-20, -74), (-18, -86), (-10, -82), (-7, -92), (2, -89), (12, -83), (17, -76), (12, -67), (5, -63)]
    pygame.draw.polygon(surface, (146, 111, 63), [point(x, y) for x, y in head])
    pygame.draw.lines(surface, PALE_GOLD, True, [point(x, y) for x, y in head], max(1, round(2 * scale)))
    pygame.draw.circle(surface, (226, 151, 78), point(7, -80), max(2, round(2.5 * scale)))
    pygame.draw.line(surface, (36, 28, 22), point(7, -72), point(15, -72), max(1, round(scale)))
    pygame.draw.polygon(surface, PALE_GOLD, [point(-18, -81), point(-28, -87), point(-22, -75)])

    for offset in range(-1, 2):
        pygame.draw.line(surface, (240, 218, 177), point(offset * 3, -56), point(offset * 3, 39), max(1, round(scale)))
    pygame.draw.circle(surface, PALE_GOLD, point(0, 27), max(2, round(2 * scale)))


def make_backdrop() -> pygame.Surface:
    surface = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        amount = y / HEIGHT
        color = (
            int(12 + amount * 11),
            int(17 + amount * 14),
            int(21 + amount * 15),
        )
        pygame.draw.line(surface, color, (0, y), (WIDTH, y))

    for position, radius, colour in (
        ((1170, 270), 390, (41, 47, 42)),
        ((1370, 530), 420, (31, 39, 38)),
        ((1010, 700), 340, (42, 42, 34)),
    ):
        halo = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(halo, (*colour, 23), (radius, radius), radius)
        surface.blit(halo, (position[0] - radius, position[1] - radius))

    rng = random.Random(38)
    for _ in range(115):
        x, y = rng.randrange(WIDTH), rng.randrange(HEIGHT)
        if y < 605:
            radius = rng.choice((1, 1, 1, 2))
            colour = rng.choice(((168, 151, 118), (113, 132, 125), (132, 131, 117)))
            pygame.draw.circle(surface, colour, (x, y), radius)

    silhouette_far = [(0, 555), (130, 474), (225, 521), (385, 400), (500, 530), (690, 438), (850, 548),
                      (1060, 406), (1200, 520), (1400, 395), (1600, 520), (1600, 900), (0, 900)]
    silhouette_near = [(0, 665), (160, 566), (325, 681), (510, 555), (685, 667), (838, 571), (1006, 679),
                       (1162, 559), (1330, 681), (1500, 555), (1600, 630), (1600, 900), (0, 900)]
    pygame.draw.polygon(surface, (24, 33, 35), silhouette_far)
    pygame.draw.polygon(surface, (18, 26, 27), silhouette_near)

    for x, y, height in ((87, 624, 145), (221, 603, 106), (1412, 609, 166), (1524, 626, 114)):
        pygame.draw.line(surface, (31, 43, 40), (x, y), (x - 6, y - height), 8)
        pygame.draw.line(surface, (31, 43, 40), (x - 6, y - height + 40), (x - 36, y - height + 68), 5)
        pygame.draw.line(surface, (31, 43, 40), (x - 5, y - height + 53), (x + 24, y - height + 81), 5)

    foreground = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.rect(foreground, (8, 9, 10, 160), (0, 0, 610, HEIGHT))
    pygame.draw.rect(foreground, (8, 9, 10, 92), (610, 0, 250, HEIGHT))
    surface.blit(foreground, (0, 0))
    return surface.convert()


class GameApp:
    def __init__(self) -> None:
        pygame.display.init()
        pygame.font.init()
        self.settings, warning = load_settings()
        self.available_voices = installed_system_voices()
        if self.settings["voice_name"] not in self.narrator_voice_choices(self.settings):
            self.settings["voice_name"] = ""
        desktop_sizes = pygame.display.get_desktop_sizes()
        if desktop_sizes:
            max_width = max(size[0] for size in desktop_sizes)
            max_height = max(size[1] for size in desktop_sizes)
            self.resolutions = [
                size for size in RESOLUTIONS
                if size[0] <= max_width and size[1] <= max_height
            ]
        else:
            self.resolutions = RESOLUTIONS.copy()
        if not self.resolutions:
            self.resolutions = [RESOLUTIONS[0]]
        if tuple(self.settings["resolution"]) not in self.resolutions:
            self.settings["resolution"] = list(self.resolutions[0])
        self.message = self.tr(warning) if warning else None
        self.message_until = time.monotonic() + 6 if warning else 0
        self.audio_available = False
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(16)
            self.audio_available = True
            self.music_tracks = {
                "menu": make_ambient_music(
                    ((73.42, 110.0, 146.83, 220.0), (65.41, 98.0, 130.81, 196.0),
                     (58.27, 87.31, 130.81, 174.61), (65.41, 98.0, 146.83, 196.0)),
                    (293.66, 220.0, 246.94, 196.0, 261.63, 220.0, 174.61, 196.0),
                ),
                "adventure": make_ambient_music(
                    ((73.42, 110.0, 146.83, 174.61), (87.31, 130.81, 174.61, 220.0),
                     (65.41, 98.0, 130.81, 196.0), (58.27, 87.31, 130.81, 174.61)),
                    (440.0, 349.23, 392.0, 293.66, 349.23, 261.63, 293.66, 220.0),
                ),
            }
            self.music_channels = (pygame.mixer.Channel(0), pygame.mixer.Channel(1))
            self.effect_channels = tuple(pygame.mixer.Channel(i) for i in range(2, 15))
            self.voice_channel = pygame.mixer.Channel(15)
            self.next_effect_channel = 0
            self.current_music_track: str | None = None
            self.ui_sound = make_sound((880.0, 1174.66), 0.075, 0.11)
            self.dice_sound = make_dice_sound()
            self.success_sound = make_sound((523.25, 659.25, 783.99), 0.48, 0.19)
            self.failure_sound = make_sound((293.66, 220.0, 174.61), 0.55, 0.16)
            self.adventure_start_sound = make_sound((392.0, 523.25, 659.25, 783.99), 0.8, 0.15)
        except pygame.error:
            self.audio_available = False
            self.voice_channel = None
            self.message = self.tr("audio_unavailable")
            self.message_until = time.monotonic() + 6

        flags = pygame.FULLSCREEN if self.settings["fullscreen"] else 0
        self.display = pygame.display.set_mode(tuple(self.settings["resolution"]), flags)
        pygame.display.set_caption("Dungeon & Bard")
        self.canvas = pygame.Surface((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.backdrop = make_backdrop()
        self.mode = "menu"
        self.onboarding_step = 1
        self.settings_return = "menu"
        self.pending = self.settings.copy()
        self.running = True
        self.buttons: dict[str, pygame.Rect] = {}
        self.sliders: dict[str, pygame.Rect] = {}
        self.dragging: str | None = None
        self.focus_field: str | None = None
        self.replace_focused_text = False
        self.backspace_held = False
        self.backspace_next_repeat = 0.0
        self.fields: dict[str, pygame.Rect] = {}
        self.d6_face = 6
        self.action_text = ""
        self.difficulty = "medium"
        self.player_count = 2
        self.duration_minutes = 60
        self.setting_text = ""
        self.extra_text = ""
        self.player_names = ["", "", ""]
        self.player_species = ["human", "human", "human"]
        self.player_classes = ["fighter", "fighter", "fighter"]
        self.player_abilities = [initial_abilities("fighter") for _ in range(3)]
        self.adventure: dict = {}
        self.story_messages: list[dict[str, str]] = []
        self.transcript_surface: pygame.Surface | None = None
        self.narration_results: queue.SimpleQueue[tuple[int, int, str | None, str | None]] = queue.SimpleQueue()
        self.adjudication_results: queue.SimpleQueue[tuple[int, int, dict | None, str | None]] = queue.SimpleQueue()
        self.narration_pending = False
        self.narration_request_id = 0
        self.adjudication_request_id = 0
        self.narration_generation = 0
        self.pending_narration_message = -1
        self.pending_narration_details = ""
        self.pending_narration_fallback = ""
        self.dice_animation_queue: list[dict[str, int | str]] = []
        self.active_dice_roll: dict[str, int | float | str] | None = None
        self.story_turn = 0
        self.last_roll: dict[str, int | str] = {}
        self.chat_scroll = 0
        self.voice_process: subprocess.Popen | None = None
        self.voice_results: queue.SimpleQueue[tuple[int, str | None, str | None]] = queue.SimpleQueue()
        self.voice_generation_thread: threading.Thread | None = None
        self.voice_cancel_event: threading.Event | None = None
        self.voice_request_id = 0
        self.voice_sound: pygame.mixer.Sound | None = None
        self.voice_queue: list[str] = []
        self.voice_ducked = False
        self.voice_muted = False
        self.current_player_index = 0
        self.quit_confirmation = False
        self.vignette = self.make_vignette()
        self.apply_audio_settings()
        self.sync_music(force=True)

    def make_vignette(self) -> pygame.Surface:
        result = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for inset in range(0, 180, 6):
            alpha = max(0, 2 + int((180 - inset) * 0.085))
            pygame.draw.rect(result, (0, 0, 0, alpha), (inset, inset, WIDTH - inset * 2, HEIGHT - inset * 2), width=7)
        return result

    def tr(self, key: str) -> str:
        return TEXT[self.settings["language"]].get(key, key)

    def set_message(self, key: str, duration: float = 3.0) -> None:
        self.message = self.tr(key)
        self.message_until = time.monotonic() + duration

    def apply_audio_settings(self, settings: dict | None = None) -> None:
        if not self.audio_available:
            return
        effective = settings or (self.pending if self.mode == "settings" else self.settings)
        master = effective["master"]
        music_volume = master * effective["music"] * (0.32 if self.voice_ducked else 1.0)
        for channel in self.music_channels:
            channel.set_volume(music_volume)
        effect_volume = master * effective["effects"]
        for channel in self.effect_channels:
            channel.set_volume(effect_volume)
        if self.voice_channel is not None:
            self.voice_channel.set_volume(master)

    def set_voice_duck(self, enabled: bool) -> None:
        if self.voice_ducked == enabled:
            return
        self.voice_ducked = enabled
        self.apply_audio_settings()

    def play_effect(self, sound: pygame.mixer.Sound) -> None:
        if self.audio_available:
            channel = self.effect_channels[self.next_effect_channel]
            self.next_effect_channel = (self.next_effect_channel + 1) % len(self.effect_channels)
            effective = self.pending if self.mode == "settings" else self.settings
            channel.set_volume(effective["master"] * effective["effects"])
            channel.play(sound)

    def sync_music(self, force: bool = False) -> None:
        if not self.audio_available:
            return
        track = "adventure" if self.mode == "chat" else "menu"
        if not force and track == self.current_music_track:
            return
        next_index = 1 if track == "adventure" else 0
        current_index = 1 - next_index
        self.music_channels[current_index].fadeout(900)
        channel = self.music_channels[next_index]
        effective = self.pending if self.mode == "settings" else self.settings
        channel.set_volume(effective["master"] * effective["music"])
        channel.play(self.music_tracks[track], loops=-1, fade_ms=900)
        self.current_music_track = track

    def narrator_locale(self, settings: dict) -> str:
        locale = settings["voice_locale"]
        return settings["language"] if locale == "auto" else locale

    def narrator_voice_choices(self, settings: dict) -> list[str]:
        locale = self.narrator_locale(settings)
        matching = [voice for voice in self.available_voices if voice["locale"] == locale]
        voices = matching or self.available_voices
        online_voices = [voice for voice, _ in NEURAL_VOICES[locale]]
        system_voices = [
            voice["name"] for voice in sorted(voices, key=voice_preference, reverse=True)
        ]
        return online_voices + [
            voice for voice in system_voices if voice not in online_voices
        ]

    def recommended_narrator_voice(self, settings: dict) -> str | None:
        locale = self.narrator_locale(settings)
        matching_system_voices = sorted(
            (
                voice
                for voice in self.available_voices
                if voice["locale"] == locale
            ),
            key=voice_preference,
            reverse=True,
        )
        online_voices = NEURAL_VOICES[locale]
        return (
            matching_system_voices[0]["name"]
            if matching_system_voices
            else online_voices[0][0]
        )

    def narrator_voice_label(self, voice_name: str) -> str:
        if voice_name in NEURAL_VOICE_LABELS:
            return f"{NEURAL_VOICE_LABELS[voice_name]} · {self.tr('voice_neural_online')}"
        return f"{voice_name} · {self.tr('voice_system_offline')}"

    def voice_is_active(self) -> bool:
        generation_active = (
            self.voice_generation_thread is not None
            and self.voice_generation_thread.is_alive()
        )
        playback_active = (
            self.voice_channel is not None and self.voice_channel.get_busy()
        )
        process_active = (
            self.voice_process is not None and self.voice_process.poll() is None
        )
        return generation_active or playback_active or process_active

    def request_quit_confirmation(self) -> None:
        if not self.quit_confirmation:
            self.quit_confirmation = True
            pygame.key.stop_text_input()

    def set_mode(self, fullscreen: bool, resolution: list[int] | tuple[int, int]) -> None:
        flags = pygame.FULLSCREEN if fullscreen else 0
        self.display = pygame.display.set_mode(tuple(resolution), flags)
        pygame.display.set_caption("Dungeon & Bard")

    def adjust_ability(self, index: int, ability: str, amount: int) -> None:
        abilities = self.player_abilities[index]
        current = abilities[ability]
        candidate = current + amount
        if candidate not in POINT_BUY_COST:
            return
        spent = point_buy_total(abilities) - POINT_BUY_COST[current] + POINT_BUY_COST[candidate]
        if spent <= 27:
            abilities[ability] = candidate

    def action_check(self, skill: str, action: str) -> tuple[dict, str, int, bool]:
        if skill == "attack":
            ability = "dexterity" if any(word in action.casefold() for word in ("arco", "frecc", "lancia", "balestra", "bow", "arrow", "crossbow", "ranged")) else "strength"
            proficient = True
        elif skill == "spellcasting":
            ability = ""
            proficient = True
        else:
            ability = SKILL_ABILITIES[skill]
            proficient = False

        mentioned = next(
            (
                character
                for character in self.adventure["characters"]
                if re.search(
                    rf"(?<!\w){re.escape(character['name'])}(?!\w)",
                    action,
                    re.IGNORECASE,
                )
            ),
            None,
        )
        candidates = [mentioned] if mentioned else self.adventure["characters"]
        if skill == "spellcasting":
            candidates = [
                character for character in candidates
                if character["class"] in {
                    "bard", "cleric", "druid", "paladin", "ranger",
                    "sorcerer", "warlock", "wizard",
                }
            ]
            if not candidates:
                return {}, "intelligence", 0, False
            ability = CLASS_DATA[candidates[0]["class"]]["primary"]

        def modifier_for(character: dict) -> int:
            used_ability = CLASS_DATA[character["class"]]["primary"] if skill == "spellcasting" else ability
            proficiency_bonus = 2 if (
                proficient or skill in CLASS_DATA[character["class"]]["skills"]
            ) else 0
            return ability_modifier(character["abilities"][used_ability]) + proficiency_bonus

        if not candidates:
            return {}, ability or "intelligence", 0, False
        character = max(candidates, key=modifier_for)
        used_ability = CLASS_DATA[character["class"]]["primary"] if skill == "spellcasting" else ability
        is_proficient = proficient or skill in CLASS_DATA[character["class"]]["skills"]
        modifier = modifier_for(character)
        return character, used_ability, modifier, is_proficient

    def narrator_history(self, limit: int = 14) -> list[dict[str, str]]:
        return [
            {"role": message["role"], "content": message["content"][:700]}
            for message in self.story_messages[-limit:]
        ]

    def party_for_narrator(self) -> list[dict]:
        language = self.settings["language"]
        return [
            {
                "name": character["name"],
                "species": self.tr(f"species_{character['species']}"),
                "class": self.tr(f"class_{character['class']}"),
                "abilities": character["abilities"].copy(),
                "skills": list(character["skills"]),
                "hit_points": character["hit_points"],
                "story_ability": " — ".join(
                    CLASS_STORY_FEATURES[character["class"]][language]
                ),
            }
            for character in self.adventure["characters"]
        ]

    def request_narration(
        self,
        request_id: int,
        generation: int,
        endpoint: str,
        token: str,
        payload: dict,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            f"{endpoint}/narrate",
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=40) as response:
                raw_response = response.read(32769)
            if len(raw_response) > 32768:
                raise ValueError("Narrator response exceeded the size limit.")
            result = json.loads(raw_response.decode("utf-8"))
            narration = result.get("narration") if isinstance(result, dict) else None
            if not isinstance(narration, str) or not 20 <= len(narration.strip()) <= 2800:
                raise ValueError("Narrator response was empty or invalid.")
            self.narration_results.put((request_id, generation, narration.strip(), None))
        except HTTPError as error:
            self.narration_results.put(
                (
                    request_id,
                    generation,
                    None,
                    "rate_limited" if error.code == 429 else "unauthorized" if error.code in (401, 403) else "unavailable",
                )
            )
        except (URLError, OSError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            self.narration_results.put((request_id, generation, None, "unavailable"))

    def request_action_adjudication(
        self,
        request_id: int,
        generation: int,
        endpoint: str,
        token: str,
        payload: dict,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            f"{endpoint}/narrate",
            data=body,
            headers={
                "Authorization": f"******",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=40) as response:
                raw_response = response.read(32769)
            if len(raw_response) > 32768:
                raise ValueError("Narrator response exceeded the size limit.")
            result = json.loads(raw_response.decode("utf-8"))
            adjudication = result.get("adjudication") if isinstance(result, dict) else None
            if not isinstance(adjudication, dict):
                raise ValueError("Narrator ruling was empty or invalid.")
            self.adjudication_results.put((request_id, generation, adjudication, None))
        except HTTPError as error:
            self.adjudication_results.put(
                (
                    request_id,
                    generation,
                    None,
                    "rate_limited" if error.code == 429 else "unauthorized" if error.code in (401, 403) else "unavailable",
                )
            )
        except (URLError, OSError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            self.adjudication_results.put((request_id, generation, None, "unavailable"))

    def begin_action_adjudication(self, message_index: int, action: str) -> bool:
        endpoint = self.settings.get("narrator_url", "").strip().rstrip("/")
        token = self.settings.get("narrator_token", "")
        if not endpoint:
            return False
        if not valid_narrator_url(endpoint):
            self.set_message("cloud_endpoint_error", 6)
            return False
        if len(token) < 24:
            self.set_message("cloud_token_required", 6)
            return False

        payload = {
            "kind": "adjudicate",
            "language": self.settings["language"],
            "setting": self.adventure["setting"],
            "extra": self.adventure["extra"],
            "difficulty": self.adventure["difficulty"],
            "action": action,
            "party": self.party_for_narrator(),
            "history": self.narrator_history()[:-2],
        }
        self.adjudication_request_id += 1
        request_id = self.adjudication_request_id
        generation = self.narration_generation
        self.pending_narration_message = message_index
        self.narration_pending = True
        self.set_message("cloud_narrating", 60)
        threading.Thread(
            target=self.request_action_adjudication,
            args=(request_id, generation, endpoint, token, payload),
            daemon=True,
            name="dungeon-bard-adjudicator",
        ).start()
        return True

    def begin_narration_request(
        self,
        message_index: int,
        payload: dict,
        mechanical_details: str = "",
        fallback_content: str = "",
    ) -> bool:
        endpoint = self.settings.get("narrator_url", "").strip().rstrip("/")
        if not endpoint:
            return False
        token = self.settings.get("narrator_token", "")
        if not valid_narrator_url(endpoint):
            self.set_message("cloud_endpoint_error", 6)
            return False
        if len(token) < 24:
            self.set_message("cloud_token_required", 6)
            return False

        self.narration_request_id += 1
        request_id = self.narration_request_id
        generation = self.narration_generation
        self.narration_pending = True
        self.set_message("cloud_narrating", 60)
        threading.Thread(
            target=self.request_narration,
            args=(request_id, generation, endpoint, token, payload),
            daemon=True,
            name="dungeon-bard-narrator",
        ).start()
        self.pending_narration_message = message_index
        self.pending_narration_details = mechanical_details
        self.pending_narration_fallback = fallback_content
        return True

    def poll_narration(self) -> None:
        while True:
            try:
                request_id, generation, narration, error = self.narration_results.get_nowait()
            except queue.Empty:
                return
            if (
                request_id != self.narration_request_id
                or generation != self.narration_generation
            ):
                continue
            self.narration_pending = False
            if error:
                self.apply_narration_fallback()
                error_message = {
                    "rate_limited": "cloud_rate_limited",
                    "unauthorized": "cloud_token_invalid",
                }.get(error, "cloud_unavailable")
                self.set_message(error_message, 8)
                continue
            if self.message == self.tr("cloud_narrating"):
                self.message = ""
                self.message_until = 0
            if narration is None:
                self.apply_narration_fallback()
                self.set_message("cloud_unavailable", 8)
                continue
            message_index = self.pending_narration_message
            if not 0 <= message_index < len(self.story_messages):
                self.apply_narration_fallback()
                self.set_message("cloud_unavailable", 8)
                continue
            message = self.story_messages[message_index]
            if message["role"] != "narrator":
                self.apply_narration_fallback()
                self.set_message("cloud_unavailable", 8)
                continue
            message["content"] = narration
            if self.pending_narration_details:
                message["content"] += f"\n\n{self.pending_narration_details}"
            self.transcript_surface = None
            self.chat_scroll = 0
            self.speak_narrator_message(message_index)

    def apply_narration_fallback(self) -> None:
        message_index = self.pending_narration_message
        if (
            self.pending_narration_fallback
            and 0 <= message_index < len(self.story_messages)
            and self.story_messages[message_index]["role"] == "narrator"
        ):
            self.story_messages[message_index]["content"] = self.pending_narration_fallback
            self.transcript_surface = None
            self.speak_narrator_message(message_index)

    def validate_action_adjudication(self, value: dict) -> bool:
        if value.get("verdict") not in ("check", "automatic", "impossible"):
            return False
        if not any(
            character["name"] == value.get("actor")
            for character in self.adventure["characters"]
        ):
            return False
        if not isinstance(value.get("reason"), str) or not value["reason"].strip():
            return False
        if value["verdict"] != "check":
            return True
        ability = value.get("ability")
        skill = value.get("skill")
        return (
            ability in ABILITY_KEYS
            and (skill is None or (
                isinstance(skill, str)
                and skill in SKILL_ABILITIES
                and SKILL_ABILITIES[skill] == ability
            ))
            and isinstance(value.get("dc"), int)
            and 5 <= value["dc"] <= 25
            and value.get("damage_die") in (None, 4, 6, 8, 10, 12)
        )

    def poll_action_adjudication(self) -> None:
        while True:
            try:
                request_id, generation, adjudication, error = self.adjudication_results.get_nowait()
            except queue.Empty:
                return
            if (
                request_id != self.adjudication_request_id
                or generation != self.narration_generation
            ):
                continue
            message_index = self.pending_narration_message
            if not 1 <= message_index < len(self.story_messages):
                self.narration_pending = False
                self.set_message("cloud_unavailable", 8)
                continue
            action_message = self.story_messages[message_index - 1]
            if action_message["role"] != "player":
                self.narration_pending = False
                self.set_message("cloud_unavailable", 8)
                continue
            action = action_message["content"]
            if error or adjudication is None or not self.validate_action_adjudication(adjudication):
                self.narration_pending = False
                error_message = {
                    "rate_limited": "cloud_rate_limited",
                    "unauthorized": "cloud_token_invalid",
                }.get(error, "cloud_unavailable")
                self.set_message(error_message, 8)
                self.resolve_local_action(action, message_index, request_narration=False)
                continue

            if adjudication["verdict"] == "check":
                self.resolve_checked_action(action, message_index, adjudication)
                continue

            payload = {
                "kind": "freeform",
                "language": self.settings["language"],
                "setting": self.adventure["setting"],
                "extra": self.adventure["extra"],
                "action": action,
                "resolution": adjudication["verdict"],
                "reason": adjudication["reason"],
                "party": self.party_for_narrator(),
                "history": self.narrator_history()[:-2],
            }
            if not self.begin_narration_request(
                message_index,
                payload,
                fallback_content=adjudication["reason"],
            ):
                message = self.story_messages[message_index]
                message["content"] = adjudication["reason"]
                self.transcript_surface = None
                self.narration_pending = False
                self.speak_narrator_message(message_index)

    def queue_dice_animation(self, sides: int, result: int, purpose: str) -> None:
        self.dice_animation_queue.append(
            {"sides": sides, "result": result, "purpose": purpose}
        )
        self.update_dice_animation()

    def update_dice_animation(self) -> None:
        now = time.monotonic()
        if self.active_dice_roll is not None:
            if now - float(self.active_dice_roll["started"]) < 1.55:
                return
            self.active_dice_roll = None
        if self.dice_animation_queue:
            self.active_dice_roll = self.dice_animation_queue.pop(0)
            self.active_dice_roll["started"] = now

    def resolve_checked_action(
        self,
        action: str,
        message_index: int,
        adjudication: dict,
        *,
        request_narration: bool = True,
    ) -> None:
        character = next(
            member
            for member in self.adventure["characters"]
            if member["name"] == adjudication["actor"]
        )
        ability = adjudication["ability"]
        skill = adjudication["skill"]
        proficient = (
            skill in character["skills"]
            if skill
            else bool(adjudication.get("proficient", False))
        )
        score = character["abilities"][ability]
        ability_bonus = ability_modifier(score)
        modifier = ability_bonus + (2 if proficient else 0)
        roll = random.randint(1, 20)
        total = roll + modifier
        target = adjudication["dc"]
        passed = total >= target
        if self.audio_available:
            self.play_effect(self.dice_sound)
            self.play_effect(self.success_sound if passed else self.failure_sound)
        self.queue_dice_animation(20, roll, "check")

        damage_roll = None
        damage_die = adjudication["damage_die"]
        if passed and damage_die is not None:
            damage_roll = {"die": damage_die, "result": random.randint(1, damage_die)}
            self.queue_dice_animation(damage_die, damage_roll["result"], "damage")

        proficiency_text = f" + {self.tr('proficiency')} +2" if proficient else ""
        check_detail = self.tr("check_detail").format(
            character=character["name"],
            class_name=self.tr(f"class_{character['class']}"),
            ability=self.tr(f"stat_{ability}"),
            score=score,
            modifier=f"{ability_bonus:+d}",
            proficiency=proficiency_text,
            total_modifier=modifier,
        )
        roll_line = self.tr("check_roll").format(
            roll=roll,
            modifier=f"{modifier:+d}",
            total=total,
            target=target,
        )
        mechanical_details = f"{check_detail}\n{roll_line}"
        check = {
            "actor": character["name"],
            "ability": self.tr(f"stat_{ability}"),
            "score": score,
            "modifier": modifier,
            "roll": roll,
            "total": total,
            "target": target,
            "passed": passed,
            "proficient": proficient,
        }
        if damage_roll is not None:
            check["damage_roll"] = damage_roll
            mechanical_details += "\n" + self.tr("damage_roll").format(
                die=f"D{damage_roll['die']}",
                result=damage_roll["result"],
            )
        action_text = self.action_text_for_narration(action, character["name"])
        fallback_content = (
            self.tr("local_check_success" if passed else "local_check_failure").format(
                actor=character["name"],
                action=action_text,
            )
            + f"\n\n{mechanical_details}"
        )

        if request_narration:
            payload = {
                "kind": "check",
                "language": self.settings["language"],
                "setting": self.adventure["setting"],
                "extra": self.adventure["extra"],
                "action": action,
                "party": self.party_for_narrator(),
                "check": check,
                "history": self.narrator_history()[:-2],
            }
            if self.begin_narration_request(
                message_index,
                payload,
                mechanical_details,
                fallback_content,
            ):
                return

        message = self.story_messages[message_index]
        message["content"] = fallback_content
        self.transcript_surface = None
        self.narration_pending = False
        self.speak_narrator_message(message_index)

    @staticmethod
    def action_text_for_narration(action: str, actor: str) -> str:
        prefix = f"{actor}: "
        text = action[len(prefix):] if action.startswith(prefix) else action
        return text.strip().rstrip(".!?")

    def resolve_local_action(
        self,
        action: str,
        message_index: int,
        *,
        request_narration: bool = True,
    ) -> None:
        skill = analyze_action(action)
        actor = next(
            (
                character for character in self.adventure["characters"]
                if action.startswith(f"{character['name']}: ")
            ),
            self.adventure["characters"][self.current_player_index],
        )
        action_text = self.action_text_for_narration(action, actor["name"])
        if skill is None:
            message = self.story_messages[message_index]
            message["content"] = self.tr("local_action").format(
                actor=actor["name"],
                action=action_text,
            )
            self.transcript_surface = None
            self.narration_pending = False
            self.speak_narrator_message(message_index)
            return

        character, ability, modifier, proficient = self.action_check(skill, action)
        if not character:
            message = self.story_messages[message_index]
            message["content"] = self.tr("local_action").format(
                actor=actor["name"],
                action=action_text,
            )
            self.transcript_surface = None
            self.narration_pending = False
            self.speak_narrator_message(message_index)
            return

        target = {"easy": 10, "medium": 13, "hard": 16}[self.adventure["difficulty"]]
        adjudication = {
            "verdict": "check",
            "actor": character["name"],
            "ability": ability,
            "skill": skill if skill in SKILL_ABILITIES else None,
            "dc": target,
            "damage_die": None,
            "reason": "",
            "proficient": proficient,
        }
        self.resolve_checked_action(
            action,
            message_index,
            adjudication,
            request_narration=request_narration,
        )

    def begin_adventure(self) -> None:
        if not self.setting_text.strip() or any(
            not self.player_names[index].strip() for index in range(self.player_count)
        ):
            self.set_message("field_required", 4)
            return
        if any(point_buy_total(self.player_abilities[index]) != 27 for index in range(self.player_count)):
            self.set_message("field_required", 4)
            return

        characters = [
            {
                "name": self.player_names[index].strip(),
                "species": self.player_species[index],
                "class": self.player_classes[index],
                "abilities": self.player_abilities[index].copy(),
                "skills": CLASS_DATA[self.player_classes[index]]["skills"],
                "hit_points": max(
                    1,
                    CLASS_DATA[self.player_classes[index]]["hit_die"]
                    + ability_modifier(self.player_abilities[index]["constitution"]),
                ),
            }
            for index in range(self.player_count)
        ]
        self.adventure = {
            "players": [character["name"] for character in characters],
            "characters": characters,
            "setting": self.setting_text.strip(),
            "extra": self.extra_text.strip(),
            "difficulty": self.difficulty,
            "duration": self.duration_minutes,
        }
        self.story_turn = 0
        self.current_player_index = 0
        self.narration_generation += 1
        self.adjudication_request_id += 1
        self.narration_pending = False
        self.chat_scroll = 0
        self.action_text = ""
        self.dice_animation_queue.clear()
        self.active_dice_roll = None
        self.story_messages = []
        setting = self.adventure["setting"].strip().rstrip(".!?")
        extra = self.adventure["extra"].strip()
        if extra and extra[-1] not in ".!?":
            extra += "."
        story = self.tr("local_opening").format(
            setting=setting,
            extra=f"\n\n{extra}" if extra else "",
        )
        self.add_story_message("narrator", story, self.tr("narrator"))
        opening_index = len(self.story_messages) - 1
        self.mode = "chat"
        started = self.begin_narration_request(
            opening_index,
            {
                "kind": "opening",
                "language": self.settings["language"],
                "setting": self.adventure["setting"],
                "extra": self.adventure["extra"],
                "duration": self.adventure["duration"],
                "difficulty": self.adventure["difficulty"],
                "party": self.party_for_narrator(),
                "history": [],
            },
            fallback_content=story,
        )
        if self.audio_available:
            self.play_effect(self.adventure_start_sound)
        self.sync_music()
        if not started:
            self.speak_narrator_message(opening_index)
        self.focus_field = "action"
        if sys.platform == "win32":
            pygame.key.start_text_input()

    def add_story_message(self, role: str, content: str, title: str = "") -> None:
        self.story_messages.append({"role": role, "content": content, "title": title})
        self.transcript_surface = None
        self.chat_scroll = 0

    def submit_action(self) -> None:
        action_text = getattr(self, "action_text", "").strip()
        if (
            self.narration_pending
            or self.active_dice_roll is not None
            or self.dice_animation_queue
        ):
            return
        if not action_text or not any(character.isalpha() for character in action_text):
            self.set_message("action_required", 4)
            return
        actor = self.adventure["characters"][self.current_player_index]
        value = f"{actor['name']}: {action_text}"
        self.add_story_message(
            "player",
            value,
            self.tr("turn_speaker").format(name=actor["name"]),
        )
        self.current_player_index = (
            self.current_player_index + 1
        ) % len(self.adventure["characters"])
        self.action_text = ""
        self.add_story_message(
            "narrator",
            self.tr("narration_wait"),
            self.tr("narrator"),
        )
        message_index = len(self.story_messages) - 1
        self.story_turn += 1
        self.focus_field = "action"
        pygame.key.start_text_input()
        if self.begin_action_adjudication(message_index, value):
            return
        self.resolve_local_action(
            value,
            message_index,
            request_narration=False,
        )
        self.chat_scroll = 0

    def narrate_latest_message(self) -> None:
        if not self.story_messages:
            return
        self.speak_narrator_message(len(self.story_messages) - 1)

    def speak_narrator_message(self, message_index: int) -> None:
        if (
            self.voice_muted
            or self.mode != "chat"
            or self.narration_pending
            or not 0 <= message_index < len(self.story_messages)
            or self.story_messages[message_index]["role"] != "narrator"
        ):
            return
        text = self.story_messages[message_index]["content"].strip()
        if not text or text == self.tr("narration_wait"):
            return
        if self.voice_is_active():
            self.voice_queue.append(text)
            return
        self.start_voice_text(text)

    def start_voice_text(self, text: str) -> None:
        voice_name = (
            self.settings.get("voice_name")
            or self.recommended_narrator_voice(self.settings)
            or ""
        )
        if voice_name in NEURAL_VOICE_IDS:
            if not self.audio_available or self.voice_channel is None:
                self.set_message("voice_error", 4)
                return
            self.start_neural_voice(text, voice_name)
            return

        if sys.platform != "win32":
            self.set_message("voice_unavailable", 4)
            return

        encoded_text = base64.b64encode(text.encode("utf-8")).decode("ascii")
        locale = self.narrator_locale(self.settings)
        encoded_voice = base64.b64encode(voice_name.encode("utf-8")).decode("ascii")
        voice_volume = round(self.settings["master"] * 100)
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Volume = {voice_volume}; "
            "$s.Rate = -1; "
            f"$culture = '{locale}'; "
            f"$requested = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded_voice}')); "
            "$voices = @($s.GetInstalledVoices()); "
            "$v = $voices | Where-Object { $_.VoiceInfo.Name -eq $requested "
            "-and $_.VoiceInfo.Culture.TwoLetterISOLanguageName -eq $culture } | Select-Object -First 1; "
            "if ($null -eq $v) { $v = $voices | Where-Object { "
            "$_.VoiceInfo.Culture.TwoLetterISOLanguageName -eq $culture } | "
            "Sort-Object @{ Expression = { if ($_.VoiceInfo.Name -match "
            "'Neural|Natural|Aria|Jenny|Zira|Elsa|Lucia|Sara|Hazel') { 0 } else { 1 } } } | "
            "Select-Object -First 1 }; "
            "if ($null -ne $v) { $s.SelectVoice($v.VoiceInfo.Name) }; "
            f"$t = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded_text}')); "
            "$s.Speak($t); $s.Dispose()"
        )
        command = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        try:
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            self.voice_process = subprocess.Popen(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-WindowStyle",
                    "Hidden",
                    "-EncodedCommand",
                    command,
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
            )
            self.set_voice_duck(True)
        except OSError:
            self.voice_process = None
            self.set_message("voice_error", 4)

    def start_neural_voice(self, text: str, voice_name: str) -> None:
        try:
            temporary_audio = tempfile.NamedTemporaryFile(
                prefix="dungeon-and-bard-voice-",
                suffix=".mp3",
                delete=False,
            )
            audio_path = Path(temporary_audio.name)
            temporary_audio.close()
        except OSError:
            self.set_message("voice_error", 4)
            return

        self.voice_request_id += 1
        request_id = self.voice_request_id
        cancel_event = threading.Event()
        self.voice_cancel_event = cancel_event
        self.set_message("voice_generating", 30)
        self.voice_generation_thread = threading.Thread(
            target=self.generate_neural_voice,
            args=(request_id, text, voice_name, audio_path, cancel_event),
            daemon=True,
            name="dungeon-bard-natural-voice",
        )
        try:
            self.voice_generation_thread.start()
        except RuntimeError:
            self.voice_generation_thread = None
            self.voice_cancel_event = None
            self.remove_temporary_voice(str(audio_path))
            self.set_message("voice_error", 4)

    def generate_neural_voice(
        self,
        request_id: int,
        text: str,
        voice_name: str,
        audio_path: Path,
        cancel_event: threading.Event,
    ) -> None:
        try:
            async def synthesize() -> None:
                request = edge_tts.Communicate(
                    text,
                    voice=voice_name,
                    rate="-5%",
                )
                await asyncio.wait_for(request.save(str(audio_path)), timeout=45)

            asyncio.run(synthesize())
            if cancel_event.is_set():
                audio_path.unlink(missing_ok=True)
                return
            self.voice_results.put((request_id, str(audio_path), None))
        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
            edge_tts.exceptions.EdgeTTSException,
            OSError,
        ):
            try:
                audio_path.unlink(missing_ok=True)
            except OSError:
                self.voice_results.put((request_id, str(audio_path), "cleanup_error"))
                return
            self.voice_results.put((request_id, None, "unavailable"))

    def stop_voice(self) -> None:
        self.voice_request_id += 1
        self.voice_queue.clear()
        if self.voice_cancel_event is not None:
            self.voice_cancel_event.set()
        if self.voice_channel is not None:
            self.voice_channel.stop()
        self.voice_sound = None
        if self.voice_process is not None and self.voice_process.poll() is None:
            self.voice_process.terminate()
        self.voice_process = None
        self.set_voice_duck(False)

    def remove_temporary_voice(self, audio_path: str) -> None:
        try:
            Path(audio_path).unlink(missing_ok=True)
        except OSError:
            self.set_message("voice_error", 4)

    def poll_voice_process(self) -> None:
        while True:
            try:
                request_id, audio_path, error = self.voice_results.get_nowait()
            except queue.Empty:
                break

            if request_id != self.voice_request_id:
                if audio_path is not None:
                    self.remove_temporary_voice(audio_path)
                continue

            self.voice_generation_thread = None
            self.voice_cancel_event = None
            if error:
                if audio_path is not None:
                    self.remove_temporary_voice(audio_path)
                self.set_message(
                    "voice_error" if error == "cleanup_error" else "voice_online_error",
                    5,
                )
                continue
            if audio_path is None or self.voice_channel is None:
                self.set_message("voice_error", 4)
                continue

            try:
                self.voice_sound = pygame.mixer.Sound(audio_path)
                self.voice_channel.set_volume(self.settings["master"])
                self.voice_channel.play(self.voice_sound)
            except pygame.error:
                self.voice_sound = None
                self.set_message("voice_error", 4)
            else:
                self.set_voice_duck(True)
                self.message = ""
                self.message_until = 0
            finally:
                self.remove_temporary_voice(audio_path)

        if (
            self.voice_generation_thread is not None
            and not self.voice_generation_thread.is_alive()
        ):
            self.voice_generation_thread = None
            if (
                self.voice_cancel_event is not None
                and self.voice_cancel_event.is_set()
            ):
                if self.message == self.tr("voice_cancelling"):
                    self.message = ""
                    self.message_until = 0
                self.voice_cancel_event = None

        if self.voice_process is not None and self.voice_process.poll() is not None:
            exit_code = self.voice_process.returncode
            self.voice_process = None
            self.set_voice_duck(False)
            if exit_code:
                self.set_message("voice_error", 4)
        if (
            not self.voice_is_active()
            and self.voice_ducked
        ):
            self.voice_sound = None
            self.set_voice_duck(False)
        if not self.voice_is_active() and self.voice_queue and not self.voice_muted:
            self.start_voice_text(self.voice_queue.pop(0))

    def start_settings(self, origin: str) -> None:
        self.settings_return = origin
        self.pending = self.settings.copy()
        self.mode = "settings"

    def apply_pending(self, return_to: str | None = None) -> None:
        narrator_url = self.pending.get("narrator_url", "").strip().rstrip("/")
        narrator_token = self.pending.get("narrator_token", "").strip()
        if narrator_url and not valid_narrator_url(narrator_url):
            self.set_message("cloud_endpoint_error", 5)
            return
        if narrator_url and len(narrator_token) < 24:
            self.set_message("cloud_token_required", 5)
            return
        self.pending["narrator_url"] = narrator_url
        self.pending["narrator_token"] = narrator_token
        previous = self.settings.copy()
        self.settings = self.pending.copy()
        try:
            self.set_mode(self.settings["fullscreen"], self.settings["resolution"])
            save_settings(self.settings)
        except (OSError, pygame.error) as error:
            self.settings = previous
            self.pending = previous.copy()
            try:
                self.set_mode(previous["fullscreen"], previous["resolution"])
            except pygame.error:
                self.running = False
            self.message = f"{self.tr('save_error')} {error}"
            self.message_until = time.monotonic() + 5
            return
        self.mode = return_to or self.settings_return
        self.apply_audio_settings()
        self.set_message("saved")
        self.sync_music(force=True)
        if not self.audio_available:
            self.message = self.tr("audio_unavailable")

    def menu_button(self, label: str, key: str, rect: pygame.Rect, mouse: tuple[int, int]) -> None:
        hovered = rect.collidepoint(mouse)
        self.buttons[key] = rect
        fill = (35, 38, 35) if hovered else (21, 25, 26)
        edge = PALE_GOLD if hovered else (105, 96, 77)
        pygame.draw.rect(self.canvas, fill, rect, border_radius=4)
        pygame.draw.rect(self.canvas, edge, rect, 1, border_radius=4)
        pygame.draw.line(self.canvas, GOLD if hovered else (124, 101, 63),
                         (rect.x + 17, rect.y + 1), (rect.right - 17, rect.y + 1))
        draw_text(self.canvas, label, rect.center, 17, PALE_GOLD if hovered else PARCHMENT,
                  centered=True, bold=True)

    def draw_brand(self, x: int = 97, y: int = 64) -> None:
        draw_dragon_mandolin(self.canvas, (x, y), 0.45)
        draw_text(self.canvas, "DUNGEON", (x + 37, y - 12), 21, PARCHMENT, font=FONT_TITLE, bold=True)
        draw_text(self.canvas, "& BARD", (x + 37, y + 11), 14, GOLD, font=FONT_TITLE)

    def draw_menu(self, mouse: tuple[int, int]) -> None:
        self.canvas.blit(self.backdrop, (0, 0))
        self.canvas.blit(self.vignette, (0, 0))
        self.draw_brand()

        ornament = pygame.Surface((500, 500), pygame.SRCALPHA)
        for radius, alpha in ((196, 44), (175, 35), (136, 28)):
            pygame.draw.circle(ornament, (222, 194, 143, alpha), (250, 250), radius, 1)
        for angle in range(0, 360, 45):
            point = (round(250 + math.cos(math.radians(angle)) * 186),
                     round(250 + math.sin(math.radians(angle)) * 186))
            pygame.draw.circle(ornament, (227, 197, 138, 82), point, 3)
        self.canvas.blit(ornament, (1004, 215))
        draw_dragon_mandolin(self.canvas, (1254, 467), 2.0)

        draw_text(self.canvas, self.tr("subtitle"), (134, 280), 12, GOLD, bold=True)
        pygame.draw.line(self.canvas, (133, 111, 75), (134, 308), (208, 308))
        draw_text(self.canvas, "DUNGEON", (128, 327), 61, (235, 226, 205), font=FONT_TITLE)
        draw_text(self.canvas, "& BARD", (130, 398), 51, GOLD, font=FONT_TITLE)
        draw_lines(self.canvas, self.tr("tagline").split(". "), (134, 480), 18, MUTED, 27)

        self.menu_button(self.tr("play"), "play", pygame.Rect(130, 575, 262, 53), mouse)
        self.menu_button(self.tr("settings"), "settings", pygame.Rect(130, 643, 262, 53), mouse)
        self.menu_button(self.tr("quit"), "quit", pygame.Rect(130, 711, 262, 53), mouse)
        draw_text(self.canvas, self.tr("footnote"), (134, 826), 10, (131, 130, 119))
        self.draw_status_message()

    def setting_row(self, label: str, value: str, key: str, y: int, mouse: tuple[int, int]) -> None:
        draw_text(self.canvas, label, (596, y + 12), 16, PARCHMENT)
        rect = pygame.Rect(840, y, 370, 45)
        self.buttons[key] = rect
        hovered = rect.collidepoint(mouse)
        pygame.draw.rect(self.canvas, (30, 32, 31) if hovered else (22, 24, 24), rect, border_radius=4)
        pygame.draw.rect(self.canvas, (155, 129, 83) if hovered else (73, 73, 67), rect, 1, border_radius=4)
        draw_text(self.canvas, "‹", (rect.x + 23, rect.centery), 24, GOLD, centered=True)
        font = get_font(FONT_BODY, 14)
        while value and font.size(value)[0] > 300:
            value = value[:-4] + "..."
        draw_text(self.canvas, value, rect.center, 14, PARCHMENT, centered=True)
        draw_text(self.canvas, "›", (rect.right - 23, rect.centery), 24, GOLD, centered=True)

    def slider_row(self, label: str, key: str, y: int, mouse: tuple[int, int]) -> None:
        draw_text(self.canvas, label, (596, y + 6), 15, PARCHMENT)
        rect = pygame.Rect(840, y + 12, 280, 10)
        self.sliders[key] = rect
        pygame.draw.rect(self.canvas, (56, 57, 52), rect, border_radius=5)
        filled = round(rect.width * self.pending[key])
        if filled:
            pygame.draw.rect(self.canvas, GOLD, (rect.x, rect.y, filled, rect.height), border_radius=5)
        thumb_x = rect.x + filled
        pygame.draw.circle(self.canvas, PALE_GOLD if rect.inflate(26, 24).collidepoint(mouse) else GOLD,
                           (thumb_x, rect.centery), 9)
        draw_text(self.canvas, f"{round(self.pending[key] * 100)}%", (1151, y + 6), 12, MUTED)

    def draw_settings(self, mouse: tuple[int, int]) -> None:
        self.canvas.blit(self.backdrop, (0, 0))
        self.canvas.blit(self.vignette, (0, 0))
        self.draw_brand()
        panel = pygame.Rect(300, 75, 1000, 755)
        outlined_panel(self.canvas, panel, (15, 18, 19), (113, 98, 70))
        draw_text(self.canvas, self.tr("settings_title"), (365, 102), 36, PARCHMENT, font=FONT_TITLE)
        draw_text(self.canvas, self.tr("display"), (365, 181), 11, GOLD, bold=True)
        pygame.draw.line(self.canvas, (65, 66, 59), (365, 203), (1235, 203))

        resolution = " × ".join(str(part) for part in self.pending["resolution"])
        self.setting_row(self.tr("resolution"), resolution, "resolution", 218, mouse)
        mode = self.tr("fullscreen" if self.pending["fullscreen"] else "windowed")
        self.setting_row(self.tr("window_mode"), mode, "fullscreen", 272, mouse)
        language = "Italiano" if self.pending["language"] == "it" else "English"
        self.setting_row(self.tr("language"), language, "language", 326, mouse)
        voice_locale = self.tr(f"voice_{self.pending['voice_locale']}")
        self.setting_row(self.tr("voice_locale"), voice_locale, "voice_locale", 380, mouse)
        selected_voice = self.pending.get("voice_name", "")
        recommended_voice = self.recommended_narrator_voice(self.pending)
        if selected_voice:
            voice_name = self.narrator_voice_label(selected_voice)
        elif recommended_voice:
            voice_name = (
                f"{self.tr('voice_recommended')}: "
                f"{self.narrator_voice_label(recommended_voice)}"
            )
        else:
            voice_name = self.tr("voice_auto")
        self.setting_row(self.tr("voice"), voice_name, "voice", 434, mouse)
        draw_text(self.canvas, self.tr("voice_privacy_hint"), (596, 466), 9, MUTED)

        draw_text(self.canvas, self.tr("cloud_narrator"), (596, 493), 12, PARCHMENT)
        cloud_status = self.tr("cloud_ready") if self.pending.get("narrator_url") else self.tr("cloud_offline")
        self.menu_button(
            f"{self.tr('cloud_configure')} · {cloud_status}",
            "cloud_configure",
            pygame.Rect(840, 477, 370, 39),
            mouse,
        )

        draw_text(self.canvas, self.tr("audio"), (365, 535), 11, GOLD, bold=True)
        pygame.draw.line(self.canvas, (65, 66, 59), (365, 557), (1235, 557))
        self.slider_row(self.tr("master_volume"), "master", 563, mouse)
        self.slider_row(self.tr("music_volume"), "music", 605, mouse)
        self.slider_row(self.tr("effects_volume"), "effects", 647, mouse)

        self.menu_button(self.tr("back"), "settings_back", pygame.Rect(365, 735, 220, 49), mouse)
        self.menu_button(self.tr("apply"), "settings_apply", pygame.Rect(1015, 735, 220, 49), mouse)
        hint = self.tr("audio_unavailable") if not self.audio_available else self.tr("back_hint")
        draw_text(self.canvas, hint, (365, 800), 9, (133, 130, 119))
        self.draw_status_message()

    def draw_cloud_settings(self, mouse: tuple[int, int]) -> None:
        self.canvas.blit(self.backdrop, (0, 0))
        self.canvas.blit(self.vignette, (0, 0))
        self.draw_brand()
        panel = pygame.Rect(300, 75, 1000, 755)
        outlined_panel(self.canvas, panel, (15, 18, 19), (113, 98, 70))
        draw_text(self.canvas, self.tr("cloud_title"), (365, 102), 32, PARCHMENT, font=FONT_TITLE)
        draw_text(self.canvas, self.tr("cloud_subtitle"), (365, 151), 13, MUTED)
        draw_text(self.canvas, self.tr("cloud_setup_hint"), (365, 203), 12, PARCHMENT)

        draw_text(self.canvas, self.tr("cloud_endpoint_label"), (365, 293), 11, GOLD, bold=True)
        self.draw_edit_field(
            "narrator_url",
            self.pending.get("narrator_url", ""),
            self.tr("cloud_endpoint_placeholder"),
            pygame.Rect(365, 316, 870, 54),
            mouse,
        )
        draw_text(self.canvas, self.tr("cloud_token_label"), (365, 401), 11, GOLD, bold=True)
        self.draw_edit_field(
            "narrator_token",
            self.pending.get("narrator_token", ""),
            self.tr("cloud_token_placeholder"),
            pygame.Rect(365, 424, 870, 54),
            mouse,
            password=True,
        )
        draw_text(self.canvas, self.tr("cloud_privacy_hint"), (365, 520), 11, MUTED)
        draw_text(
            self.canvas,
            self.tr("cloud_clipboard_error") if self.message == self.tr("cloud_clipboard_error") else "",
            (365, 552),
            10,
            MUTED,
        )
        self.menu_button(
            self.tr("cloud_back"),
            "cloud_back",
            pygame.Rect(365, 735, 220, 49),
            mouse,
        )
        self.menu_button(
            self.tr("cloud_apply"),
            "cloud_apply",
            pygame.Rect(1015, 735, 220, 49),
            mouse,
        )
        self.draw_status_message()

    def draw_edit_field(
        self,
        key: str,
        value: str,
        placeholder: str,
        rect: pygame.Rect,
        mouse: tuple[int, int],
        *,
        multiline: bool = False,
        password: bool = False,
    ) -> None:
        self.fields[key] = rect
        focused = self.focus_field == key
        border = GOLD if focused or rect.collidepoint(mouse) else (71, 72, 66)
        pygame.draw.rect(self.canvas, (20, 23, 23), rect, border_radius=5)
        pygame.draw.rect(self.canvas, border, rect, 1, border_radius=5)
        visible_value = "*" * len(value) if password and value else value
        shown = visible_value or placeholder
        colour = PARCHMENT if value else (115, 116, 108)
        max_width = rect.width - 30
        if multiline:
            lines = self.wrap_text(shown, max_width)
            for index, line in enumerate(lines[:3]):
                draw_text(self.canvas, line, (rect.x + 14, rect.y + 12 + index * 23), 14, colour)
            if focused and int(time.monotonic() * 2) % 2 == 0:
                cursor_y = rect.y + 12 + min(len(lines) - 1, 2) * 23
                pygame.draw.line(self.canvas, PALE_GOLD, (rect.x + 15, cursor_y),
                                 (rect.x + 15, cursor_y + 17), 2)
        else:
            visible = visible_value
            font = get_font(FONT_BODY, 14)
            while visible and font.size(visible)[0] > max_width:
                visible = visible[1:]
            draw_text(self.canvas, visible or shown, (rect.x + 14, rect.y + 13), 14, colour)
            if focused and int(time.monotonic() * 2) % 2 == 0:
                cursor_x = rect.x + 14 + font.size(visible)[0]
                pygame.draw.line(self.canvas, PALE_GOLD, (cursor_x, rect.y + 12), (cursor_x, rect.y + 30), 2)

    @staticmethod
    def wrap_text(value: str, max_width: int, size: int = 14) -> list[str]:
        font = get_font(FONT_BODY, size)
        result: list[str] = []
        for paragraph in value.splitlines() or [""]:
            words = paragraph.split()
            line = ""
            for word in words:
                candidate = f"{line} {word}".strip()
                if line and font.size(candidate)[0] > max_width:
                    result.append(line)
                    line = word
                else:
                    line = candidate
            result.append(line)
        return result

    def build_transcript(self, width: int) -> pygame.Surface:
        layout: list[tuple[int, int, dict[str, str], list[str], int, int]] = []
        total_height = 28
        for message in self.story_messages:
            is_player = message["role"] == "player"
            bubble_width = min(760 if is_player else 890, width)
            text_width = bubble_width - 34
            title_lines = self.wrap_text(message["title"], text_width, 11) if message["title"] else []
            body_lines: list[str] = []
            for paragraph in message["content"].splitlines():
                body_lines.extend(self.wrap_text(paragraph, text_width, 14))
                if paragraph:
                    body_lines.append("")
            while body_lines and not body_lines[-1]:
                body_lines.pop()
            body_lines = body_lines or [""]
            bubble_height = max(61, 19 + len(title_lines) * 22 + len(body_lines) * 23)
            layout.append(
                (total_height, bubble_width, message, title_lines + body_lines, bubble_height, len(title_lines))
            )
            total_height += bubble_height + 13

        surface = pygame.Surface((width, max(1, total_height)), pygame.SRCALPHA)
        for y, bubble_width, message, lines, bubble_height, title_count in layout:
            is_player = message["role"] == "player"
            x = width - bubble_width if is_player else 0
            rect = pygame.Rect(x, y, bubble_width, bubble_height)
            fill = (31, 39, 34) if is_player else (27, 29, 28)
            border = (104, 108, 80) if is_player else (77, 73, 60)
            pygame.draw.rect(surface, fill, rect, border_radius=9)
            pygame.draw.rect(surface, border, rect, 1, border_radius=9)
            offset_y = rect.y + 12
            for index, line in enumerate(lines):
                is_title = index < title_count
                if line:
                    draw_text(
                        surface,
                        line,
                        (rect.x + 15, offset_y),
                        11 if is_title else 14,
                        (PALE_GOLD if not is_player else (170, 192, 154))
                        if is_title
                        else PARCHMENT,
                        bold=is_title,
                    )
                offset_y += 22 if is_title else 23
        return surface

    def counter_button(
        self,
        key: str,
        rect: pygame.Rect,
        label: str,
        mouse: tuple[int, int],
        *,
        enabled: bool = True,
    ) -> None:
        if enabled:
            self.buttons[key] = rect
        hovered = rect.collidepoint(mouse)
        fill = (37, 39, 36) if hovered and enabled else (23, 26, 26)
        edge = GOLD if hovered and enabled else ((81, 79, 70) if enabled else (48, 49, 45))
        pygame.draw.rect(self.canvas, fill, rect, border_radius=4)
        pygame.draw.rect(self.canvas, edge, rect, 1, border_radius=4)
        draw_text(self.canvas, label, rect.center, 18, PALE_GOLD if enabled else MUTED, centered=True)

    def setting_row_button(
        self,
        label: str,
        value: str,
        key: str,
        rect: pygame.Rect,
        mouse: tuple[int, int],
    ) -> None:
        self.buttons[key] = rect
        hovered = rect.collidepoint(mouse)
        pygame.draw.rect(self.canvas, (34, 36, 33) if hovered else (23, 26, 26), rect, border_radius=4)
        pygame.draw.rect(self.canvas, GOLD if hovered else (81, 79, 70), rect, 1, border_radius=4)
        draw_text(self.canvas, "‹", (rect.x + 12, rect.centery), 16, GOLD, centered=True)
        draw_text(self.canvas, f"{label}: {value}", rect.center, 9, PARCHMENT, centered=True)
        draw_text(self.canvas, "›", (rect.right - 12, rect.centery), 16, GOLD, centered=True)

    def character_option_button(
        self,
        label: str,
        value: str,
        key: str,
        rect: pygame.Rect,
        mouse: tuple[int, int],
    ) -> None:
        arrow_width = 36
        self.buttons[f"{key}_prev"] = pygame.Rect(rect.x, rect.y, arrow_width, rect.height)
        self.buttons[f"{key}_next"] = pygame.Rect(rect.right - arrow_width, rect.y, arrow_width, rect.height)
        self.buttons[key] = pygame.Rect(
            rect.x + arrow_width,
            rect.y,
            rect.width - arrow_width * 2,
            rect.height,
        )
        hovered = rect.collidepoint(mouse)
        pygame.draw.rect(self.canvas, (34, 36, 33) if hovered else (23, 26, 26), rect, border_radius=4)
        pygame.draw.rect(self.canvas, GOLD if hovered else (81, 79, 70), rect, 1, border_radius=4)
        draw_text(self.canvas, label, (rect.x + 31, rect.y + 6), 8, GOLD, bold=True)
        draw_text(self.canvas, value, rect.center, 13, PARCHMENT, centered=True)
        draw_text(self.canvas, "‹", (rect.x + 12, rect.centery), 16, GOLD, centered=True)
        draw_text(self.canvas, "›", (rect.right - 12, rect.centery), 16, GOLD, centered=True)

    def draw_onboarding(self, mouse: tuple[int, int]) -> None:
        self.canvas.blit(self.backdrop, (0, 0))
        self.canvas.blit(self.vignette, (0, 0))
        self.draw_brand()
        panel = pygame.Rect(235, 70, 1130, 760)
        outlined_panel(self.canvas, panel, (15, 18, 19), (113, 98, 70))
        draw_text(self.canvas, self.tr("create_title"), (280, 89), 34, PARCHMENT, font=FONT_TITLE)
        draw_text(self.canvas, self.tr("create_subtitle"), (282, 132), 13, MUTED)
        draw_text(self.canvas, self.tr("step_adventure"), (1280, 104), 10, GOLD, centered=True, bold=True)

        draw_text(self.canvas, self.tr("players"), (282, 180), 10, GOLD, bold=True)
        self.counter_button("players_less", pygame.Rect(634, 177, 42, 37), "−", mouse)
        draw_text(
            self.canvas,
            self.tr("players_count_one")
            if self.player_count == 1
            else self.tr("players_count_many").format(count=self.player_count),
            (712, 188),
            15,
            PARCHMENT,
            centered=True,
        )
        self.counter_button("players_more", pygame.Rect(747, 177, 42, 37), "+", mouse)

        draw_text(self.canvas, self.tr("duration"), (850, 180), 10, GOLD, bold=True)
        self.counter_button("duration_less", pygame.Rect(1104, 177, 42, 37), "−", mouse)
        draw_text(self.canvas, f"{self.duration_minutes} {self.tr('minutes')}", (1190, 188), 14, PARCHMENT, centered=True)
        self.counter_button("duration_more", pygame.Rect(1264, 177, 42, 37), "+", mouse)

        draw_text(self.canvas, self.tr("difficulty"), (282, 239), 10, GOLD, bold=True)
        options = [
            ("easy", self.tr("easy"), self.tr("easy_desc")),
            ("medium", self.tr("medium"), self.tr("medium_desc")),
            ("hard", self.tr("hard"), self.tr("hard_desc")),
        ]
        for index, (key, title, description) in enumerate(options):
            rect = pygame.Rect(282 + index * 342, 263, 322, 69)
            self.buttons[f"difficulty_{key}"] = rect
            active = self.difficulty == key
            border = GOLD if active else ((99, 91, 73) if rect.collidepoint(mouse) else (67, 68, 61))
            pygame.draw.rect(self.canvas, (36, 35, 29) if active else (21, 24, 24), rect, border_radius=5)
            pygame.draw.rect(self.canvas, border, rect, 1, border_radius=5)
            draw_text(self.canvas, title, (rect.x + 14, rect.y + 11), 15,
                      PALE_GOLD if active else PARCHMENT, bold=True)
            draw_text(self.canvas, description, (rect.x + 14, rect.y + 40), 11, MUTED)

        draw_text(self.canvas, self.tr("setting"), (282, 355), 10, GOLD, bold=True)
        setting_rect = pygame.Rect(282, 378, 926, 84)
        self.draw_edit_field(
            "setting", self.setting_text, self.tr("setting_placeholder"), setting_rect, mouse, multiline=True
        )
        dice_rect = pygame.Rect(1220, 378, 86, 84)
        self.buttons["random_setting"] = dice_rect
        hovered = dice_rect.collidepoint(mouse)
        pygame.draw.rect(self.canvas, (39, 37, 30) if hovered else (23, 25, 24), dice_rect, border_radius=5)
        pygame.draw.rect(self.canvas, GOLD if hovered else (94, 82, 61), dice_rect, 1, border_radius=5)
        die = pygame.Rect(dice_rect.centerx - 13, dice_rect.y + 13, 26, 26)
        pygame.draw.rect(self.canvas, PALE_GOLD, die, border_radius=5)
        pip_layouts = {
            1: [(0, 0)],
            2: [(-6, -6), (6, 6)],
            3: [(-7, -7), (0, 0), (7, 7)],
            4: [(-7, -7), (7, -7), (-7, 7), (7, 7)],
            5: [(-7, -7), (7, -7), (0, 0), (-7, 7), (7, 7)],
            6: [(-7, -8), (7, -8), (-7, 0), (7, 0), (-7, 8), (7, 8)],
        }
        for pip_x, pip_y in pip_layouts[self.d6_face]:
            pygame.draw.circle(self.canvas, (38, 38, 32), (die.centerx + pip_x, die.centery + pip_y), 2)
        draw_text(self.canvas, "D6", (dice_rect.centerx, dice_rect.y + 60), 10, PARCHMENT, centered=True, bold=True)

        draw_text(self.canvas, self.tr("extra"), (282, 520), 10, GOLD, bold=True)
        extra_rect = pygame.Rect(282, 543, 1024, 46)
        self.draw_edit_field(
            "extra", self.extra_text, self.tr("extra_placeholder"), extra_rect, mouse
        )
        self.menu_button(
            self.tr("continue_characters"),
            "character_next",
            pygame.Rect(662, 737, 644, 51),
            mouse,
        )
        self.menu_button(
            self.tr("back"),
            "go_back",
            pygame.Rect(282, 737, 350, 51),
            mouse,
        )
        self.draw_status_message()

    def draw_character_setup(self, mouse: tuple[int, int]) -> None:
        self.canvas.blit(self.backdrop, (0, 0))
        self.canvas.blit(self.vignette, (0, 0))
        self.draw_brand()
        panel = pygame.Rect(235, 70, 1130, 760)
        outlined_panel(self.canvas, panel, (15, 18, 19), (113, 98, 70))
        draw_text(self.canvas, self.tr("character_page_title"), (280, 89), 34, PARCHMENT, font=FONT_TITLE)
        draw_text(self.canvas, self.tr("character_page_subtitle"), (282, 132), 12, MUTED)
        step_text = self.tr("step_characters")
        draw_text(self.canvas, step_text, (1280, 104), 10, GOLD, centered=True, bold=True)

        gap = 18
        available_width = 1064
        card_width = min(760, (available_width - gap * (self.player_count - 1)) // self.player_count)
        total_width = card_width * self.player_count + gap * (self.player_count - 1)
        start_x = (WIDTH - total_width) // 2
        card_y = 190
        card_height = 548
        abbreviations = self.tr("ability_short")

        for index in range(self.player_count):
            x = start_x + index * (card_width + gap)
            card = pygame.Rect(x, card_y, card_width, card_height)
            outlined_panel(self.canvas, card, (18, 21, 21), (83, 78, 64))
            draw_text(
                self.canvas,
                self.tr("character_number").format(number=index + 1),
                (card.x + 18, card.y + 18),
                12,
                GOLD,
                bold=True,
            )
            name_rect = pygame.Rect(card.x + 16, card.y + 43, card.width - 32, 42)
            self.draw_edit_field(
                f"player_{index}",
                self.player_names[index],
                f"{self.tr('character_placeholder')} {index + 1}",
                name_rect,
                mouse,
            )
            species_rect = pygame.Rect(card.x + 16, card.y + 94, card.width - 32, 42)
            self.character_option_button(
                self.tr("species"),
                self.tr(f"species_{self.player_species[index]}"),
                f"species_{index}",
                species_rect,
                mouse,
            )
            class_rect = pygame.Rect(card.x + 16, card.y + 145, card.width - 32, 42)
            self.character_option_button(
                self.tr("class"),
                self.tr(f"class_{self.player_classes[index]}"),
                f"class_{index}",
                class_rect,
                mouse,
            )

            draw_text(
                self.canvas,
                self.tr("class_feature"),
                (card.x + 18, card.y + 194),
                8,
                GOLD,
                bold=True,
            )
            feature_name, feature_description = CLASS_STORY_FEATURES[
                self.player_classes[index]
            ][self.settings["language"]]
            draw_text(
                self.canvas,
                f"{feature_name} · {feature_description}",
                (card.x + 18, card.y + 210),
                8,
                PALE_GOLD,
            )
            draw_text(
                self.canvas,
                self.tr("character_stats"),
                (card.x + 18, card.y + 233),
                10,
                GOLD,
                bold=True,
            )
            draw_text(
                self.canvas,
                self.tr("character_summary"),
                (card.x + 18, card.y + 253),
                9,
                MUTED,
            )

            for ability_index, ability in enumerate(ABILITY_KEYS):
                row = pygame.Rect(card.x + 16, card.y + 276 + ability_index * 39, card.width - 32, 34)
                hovered = row.collidepoint(mouse)
                pygame.draw.rect(
                    self.canvas,
                    (31, 33, 31) if hovered else (22, 25, 25),
                    row,
                    border_radius=4,
                )
                pygame.draw.rect(
                    self.canvas,
                    (74, 73, 66),
                    row,
                    1,
                    border_radius=4,
                )
                draw_text(
                    self.canvas,
                    abbreviations[ability_index],
                    (row.x + 12, row.centery),
                    11,
                    PARCHMENT,
                    centered=False,
                    bold=True,
                )
                score = self.player_abilities[index][ability]
                score_modifier = ability_modifier(score)
                minus = pygame.Rect(row.right - 129, row.y + 4, 24, 26)
                score_rect = pygame.Rect(row.right - 99, row.y + 4, 42, 26)
                plus = pygame.Rect(row.right - 51, row.y + 4, 24, 26)
                self.counter_button(
                    f"ability_{index}_{ability}_dec",
                    minus,
                    "−",
                    mouse,
                    enabled=score > 8,
                )
                pygame.draw.rect(self.canvas, (18, 21, 21), score_rect, border_radius=4)
                pygame.draw.rect(self.canvas, (81, 79, 70), score_rect, 1, border_radius=4)
                draw_text(
                    self.canvas,
                    f"{score}",
                    score_rect.center,
                    11,
                    PALE_GOLD,
                    centered=True,
                )
                spent_without_score = point_buy_total(self.player_abilities[index]) - POINT_BUY_COST[score]
                can_increase = score < 15 and spent_without_score + POINT_BUY_COST[score + 1] <= 27
                self.counter_button(
                    f"ability_{index}_{ability}_inc",
                    plus,
                    "+",
                    mouse,
                    enabled=can_increase,
                )
                draw_text(
                    self.canvas,
                    f"{score_modifier:+d}",
                    (row.right - 14, row.centery),
                    10,
                    MUTED,
                    centered=True,
                )

            hp = max(
                1,
                CLASS_DATA[self.player_classes[index]]["hit_die"]
                + ability_modifier(self.player_abilities[index]["constitution"]),
            )
            draw_text(
                self.canvas,
                self.tr("character_health").format(hp=hp),
                (card.centerx, card.bottom - 20),
                10,
                PALE_GOLD,
                centered=True,
            )

        self.menu_button(
            self.tr("back_adventure"),
            "character_back",
            pygame.Rect(282, 759, 350, 47),
            mouse,
        )
        self.menu_button(
            self.tr("start_adventure"),
            "start_adventure",
            pygame.Rect(662, 759, 644, 47),
            mouse,
        )
        self.draw_status_message()

    def draw_dice_animation(self) -> None:
        if self.active_dice_roll is None:
            return
        roll = self.active_dice_roll
        sides = int(roll["sides"])
        result = int(roll["result"])
        elapsed = max(0.0, time.monotonic() - float(roll["started"]))
        is_rolling = elapsed < 0.95
        frame = int(elapsed * 19)
        display_result = (
            random.Random(result * 1009 + sides * 37 + frame).randint(1, sides)
            if is_rolling
            else result
        )
        panel = pygame.Rect(610, 337, 380, 260)
        pygame.draw.rect(self.canvas, (10, 13, 14), panel, border_radius=10)
        pygame.draw.rect(self.canvas, GOLD, panel, 2, border_radius=10)
        purpose_key = "dice_damage_label" if roll["purpose"] == "damage" else "dice_check_label"
        draw_text(
            self.canvas,
            self.tr(purpose_key),
            (panel.centerx, panel.y + 29),
            11,
            GOLD,
            centered=True,
            bold=True,
        )
        draw_text(
            self.canvas,
            self.tr("dice_rolling") if is_rolling else self.tr("dice_result").format(
                die=f"D{sides}",
                result=result,
            ),
            (panel.centerx, panel.y + 56),
            13,
            PARCHMENT,
            centered=True,
        )

        vertex_counts = {4: 3, 6: 4, 8: 6, 10: 5, 12: 6, 20: 8}
        vertex_count = vertex_counts[sides]
        rotation = elapsed * 5.2
        bob = math.sin(elapsed * 12) * (12 if is_rolling else 0)
        center = (panel.centerx, round(panel.y + 139 + bob))
        radius = 56
        points = [
            (
                round(center[0] + math.cos(rotation + 2 * math.pi * index / vertex_count) * radius),
                round(center[1] + math.sin(rotation + 2 * math.pi * index / vertex_count) * radius),
            )
            for index in range(vertex_count)
        ]
        pygame.draw.polygon(self.canvas, (42, 48, 42), points)
        pygame.draw.polygon(self.canvas, PALE_GOLD, points, 3)
        for index in range(0, vertex_count, 2):
            pygame.draw.line(self.canvas, (130, 116, 82), center, points[index], 1)
        draw_text(
            self.canvas,
            str(display_result),
            center,
            27,
            PARCHMENT,
            centered=True,
            bold=True,
        )
        draw_text(
            self.canvas,
            f"D{sides}",
            (panel.centerx, panel.bottom - 23),
            11,
            MUTED,
            centered=True,
        )

    def draw_chat(self, mouse: tuple[int, int]) -> None:
        self.canvas.blit(self.backdrop, (0, 0))
        self.canvas.blit(self.vignette, (0, 0))
        self.draw_brand()
        draw_text(self.canvas, self.tr("adventure"), (800, 43), 10, GOLD, centered=True, bold=True)
        draw_text(self.canvas, self.tr("narrator"), (800, 69), 19, PARCHMENT, font=FONT_TITLE, centered=True)


        current_player = self.adventure["characters"][self.current_player_index]["name"]
        draw_text(
            self.canvas,
            self.tr("turn_display").format(
                name=current_player,
                duration=self.adventure["duration"],
            ),
            (800, 98),
            11,
            MUTED,
            centered=True,
        )
        panel = pygame.Rect(232, 127, 1136, 549)
        outlined_panel(self.canvas, panel, (14, 17, 18), (92, 82, 62))
        title_rect = pygame.Rect(panel.x + 1, panel.y + 1, panel.width - 2, 45)
        pygame.draw.rect(self.canvas, (25, 27, 26), title_rect, border_top_left_radius=5, border_top_right_radius=5)
        draw_text(self.canvas, self.tr("setting"), (panel.x + 20, panel.y + 14), 9, GOLD, bold=True)
        setting_lines = self.wrap_text(self.adventure["setting"], 850, 10)
        draw_text(self.canvas, " ".join(setting_lines[:1]), (panel.x + 243, panel.y + 14), 10, MUTED)
        draw_text(
            self.canvas,
            self.tr("turn_count").format(count=self.story_turn),
            (panel.right - 90, panel.y + 14),
            10,
            MUTED,
        )

        transcript = pygame.Rect(panel.x + 20, panel.y + 61, panel.width - 40, panel.height - 78)
        if self.transcript_surface is None:
            self.transcript_surface = self.build_transcript(transcript.width)
        max_scroll = max(0, self.transcript_surface.height - transcript.height)
        self.chat_scroll = min(self.chat_scroll, max_scroll)
        y_offset = transcript.bottom - self.transcript_surface.height + self.chat_scroll
        self.canvas.set_clip(transcript)
        self.canvas.blit(self.transcript_surface, (transcript.x, y_offset))
        self.canvas.set_clip(None)
        self.draw_dice_animation()

        self.fields["action_text"] = pygame.Rect(232, 697, 831, 65)
        focused = self.focus_field == "action"
        input_rect = self.fields["action_text"]
        pygame.draw.rect(self.canvas, (19, 22, 22), input_rect, border_radius=5)
        pygame.draw.rect(self.canvas, GOLD if focused else (82, 79, 69), input_rect, 1, border_radius=5)
        dice_is_rolling = self.active_dice_roll is not None or bool(self.dice_animation_queue)
        if self.narration_pending or dice_is_rolling:
            text = self.tr("narration_wait")
            input_colour = MUTED
        else:
            text = self.action_text or self.tr("action_placeholder").format(
                player=current_player,
            )
            input_colour = PARCHMENT if self.action_text else (115, 116, 108)
        visible = text[-92:]
        draw_text(self.canvas, visible, (input_rect.x + 16, input_rect.y + 23), 14, input_colour)
        if focused and not self.narration_pending and not dice_is_rolling and int(time.monotonic() * 2) % 2 == 0:
            font = pygame.font.SysFont(FONT_BODY, 14)
            cursor = min(input_rect.right - 12, input_rect.x + 16 + font.size(visible)[0])
            pygame.draw.line(self.canvas, PALE_GOLD, (cursor, input_rect.y + 20), (cursor, input_rect.y + 42), 2)

        voice_label = self.tr("unmute_voice" if self.voice_muted else "mute_voice")
        self.menu_button(voice_label, "toggle_mute", pygame.Rect(1080, 697, 130, 65), mouse)
        send_label = self.tr("narration_send") if self.narration_pending or dice_is_rolling else self.tr("send")
        self.menu_button(send_label, "send_action", pygame.Rect(1226, 697, 142, 65), mouse)
        self.menu_button(
            self.tr("new_adventure"),
            "new_adventure",
            pygame.Rect(232, 780, 260, 45),
            mouse,
        )
        self.menu_button(
            self.tr("back"),
            "go_back",
            pygame.Rect(510, 780, 220, 45),
            mouse,
        )
        self.draw_status_message()

    def draw_status_message(self) -> None:
        if self.message and time.monotonic() < self.message_until:
            draw_text(self.canvas, self.message[:105], (WIDTH // 2, HEIGHT - 25), 13,
                      (231, 173, 130), centered=True)

    def draw_quit_confirmation(self, mouse: tuple[int, int]) -> None:
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 190))
        self.canvas.blit(veil, (0, 0))
        panel = pygame.Rect(470, 316, 660, 268)
        outlined_panel(self.canvas, panel, (15, 18, 19), (173, 143, 91))
        draw_text(
            self.canvas,
            self.tr("quit_title"),
            (WIDTH // 2, panel.y + 55),
            29,
            PARCHMENT,
            font=FONT_TITLE,
            centered=True,
        )
        draw_text(self.canvas, self.tr("quit_hint"), (WIDTH // 2, panel.y + 111), 13, MUTED, centered=True)
        self.menu_button(
            self.tr("quit_cancel"),
            "quit_cancel",
            pygame.Rect(panel.x + 36, panel.y + 166, 285, 54),
            mouse,
        )
        self.menu_button(
            self.tr("quit_confirm"),
            "quit_confirm",
            pygame.Rect(panel.right - 321, panel.y + 166, 285, 54),
            mouse,
        )

    def activate_button(self, key: str) -> None:
        if self.audio_available:
            self.play_effect(self.ui_sound)
        if key == "go_back":
            self.go_back()
        elif key == "play":
            self.focus_field = None
            self.mode = "onboarding"
            self.onboarding_step = 1
        elif key == "settings":
            self.start_settings("menu")
        elif key == "cloud_configure":
            self.mode = "cloud_settings"
            self.focus_field = None
        elif key == "cloud_back":
            self.mode = "settings"
            self.focus_field = None
        elif key == "cloud_apply":
            self.pending["narrator_token"] = self.pending.get("narrator_token", "").strip()
            self.apply_pending(return_to="settings")
        elif key == "quit":
            self.request_quit_confirmation()
        elif key == "quit_confirm":
            self.running = False
            self.quit_confirmation = False
        elif key == "quit_cancel":
            self.quit_confirmation = False
            if self.focus_field is not None and self.mode in ("onboarding", "chat", "cloud_settings"):
                pygame.key.start_text_input()
        elif key == "settings_back":
            self.mode = self.settings_return
            self.apply_audio_settings(self.settings)
            self.sync_music(force=True)
        elif key == "settings_apply":
            self.apply_pending()
        elif key == "start_adventure":
            self.begin_adventure()
        elif key == "send_action" and self.narration_pending:
            return
        elif key == "character_next":
            if not self.setting_text.strip():
                self.set_message("setting_required", 4)
            else:
                self.focus_field = None
                self.onboarding_step = 2
        elif key == "character_back":
            self.focus_field = None
            self.onboarding_step = 1
        elif key == "send_action":
            self.submit_action()
        elif key == "listen":
            self.narrate_latest_message()
        elif key == "toggle_mute":
            self.voice_muted = not self.voice_muted
            if self.voice_muted:
                self.stop_voice()
            else:
                self.narrate_latest_message()
        elif key == "new_adventure":
            self.stop_voice()
            self.focus_field = None
            self.mode = "onboarding"
            self.onboarding_step = 1
            self.narration_generation += 1
            self.adjudication_request_id += 1
            self.narration_pending = False
            self.dice_animation_queue.clear()
            self.active_dice_roll = None
        elif key.startswith("difficulty_"):
            self.difficulty = key.removeprefix("difficulty_")
        elif key == "players_less":
            self.player_count = max(1, self.player_count - 1)
        elif key == "players_more":
            self.player_count = min(3, self.player_count + 1)
        elif key == "duration_less":
            choices = (15, 30, 45, 60, 90, 120, 180)
            index = choices.index(self.duration_minutes)
            self.duration_minutes = choices[max(0, index - 1)]
        elif key == "duration_more":
            choices = (15, 30, 45, 60, 90, 120, 180)
            index = choices.index(self.duration_minutes)
            self.duration_minutes = choices[min(len(choices) - 1, index + 1)]
        elif key == "random_setting":
            self.d6_face = random.randint(1, 6)
            self.setting_text = generate_random_setting(self.settings["language"])
            self.focus_field = "setting"
            self.replace_focused_text = True
            pygame.key.start_text_input()
        elif key.startswith("species_"):
            index = int(key.removeprefix("species_").split("_", 1)[0])
            current = self.player_species[index]
            direction = -1 if key.endswith("_prev") else 1
            self.player_species[index] = SPECIES_KEYS[
                (SPECIES_KEYS.index(current) + direction) % len(SPECIES_KEYS)
            ]
        elif key.startswith("class_"):
            index = int(key.removeprefix("class_").split("_", 1)[0])
            current = self.player_classes[index]
            direction = -1 if key.endswith("_prev") else 1
            next_class = CLASS_KEYS[(CLASS_KEYS.index(current) + direction) % len(CLASS_KEYS)]
            if self.player_abilities[index] == initial_abilities(current):
                self.player_abilities[index] = initial_abilities(next_class)
            self.player_classes[index] = next_class
        elif key.startswith("ability_") and not key.endswith("_score"):
            _, index_text, ability, direction = key.split("_")
            self.adjust_ability(int(index_text), ability, 1 if direction == "inc" else -1)
        elif key == "resolution":
            current = tuple(self.pending["resolution"])
            index = self.resolutions.index(current) if current in self.resolutions else -1
            self.pending["resolution"] = list(self.resolutions[(index + 1) % len(self.resolutions)])
        elif key == "fullscreen":
            self.pending["fullscreen"] = not self.pending["fullscreen"]
        elif key == "language":
            self.pending["language"] = "en" if self.pending["language"] == "it" else "it"
        elif key == "voice_locale":
            voices = ("auto", "it", "en")
            current = self.pending["voice_locale"]
            index = voices.index(current) if current in voices else 0
            self.pending["voice_locale"] = voices[(index + 1) % len(voices)]
            if self.pending.get("voice_name") not in self.narrator_voice_choices(self.pending):
                self.pending["voice_name"] = ""
        elif key == "voice":
            choices = [""] + self.narrator_voice_choices(self.pending)
            current = self.pending.get("voice_name", "")
            index = choices.index(current) if current in choices else 0
            self.pending["voice_name"] = choices[(index + 1) % len(choices)]

    def go_back(self) -> None:
        self.focus_field = None
        self.replace_focused_text = False
        pygame.key.stop_text_input()

        if self.mode == "menu":
            self.request_quit_confirmation()
        elif self.mode == "settings":
            self.mode = self.settings_return
            self.apply_audio_settings(self.settings)
            self.sync_music(force=True)
        elif self.mode == "cloud_settings":
            self.mode = "settings"
        elif self.mode == "onboarding":
            if self.onboarding_step == 2:
                self.onboarding_step = 1
            else:
                self.mode = "menu"
                self.sync_music(force=True)
        elif self.mode == "chat":
            self.stop_voice()
            self.mode = "onboarding"
            self.onboarding_step = 2
            self.narration_generation += 1
            self.adjudication_request_id += 1
            self.narration_pending = False
            self.dice_animation_queue.clear()
            self.active_dice_roll = None
            self.sync_music(force=True)

    def handle_click(self, position: tuple[int, int]) -> None:
        if self.mode in ("onboarding", "chat", "cloud_settings"):
            clicked_field = next(
                (key for key, rect in self.fields.items() if rect.collidepoint(position)),
                None,
            )
            if clicked_field is not None:
                if self.mode == "chat":
                    if self.narration_pending:
                        return
                    self.focus_field = "action"
                else:
                    self.focus_field = clicked_field
                self.replace_focused_text = False
                pygame.key.start_text_input()
                return
            self.focus_field = None
            pygame.key.stop_text_input()
        for key, rect in self.buttons.items():
            if rect.collidepoint(position):
                self.activate_button(key)
                return

    def handle_text_input(self, value: str) -> None:
        if self.mode == "chat" and self.focus_field == "action":
            if self.narration_pending or self.active_dice_roll is not None or self.dice_animation_queue:
                return
            self.action_text = (self.action_text + value)[-300:]
            return
        if self.mode == "cloud_settings" and self.focus_field in ("narrator_url", "narrator_token"):
            replace = self.replace_focused_text
            self.replace_focused_text = False
            current = "" if replace else self.pending.get(self.focus_field, "")
            maximum = 300 if self.focus_field == "narrator_url" else 256
            self.pending[self.focus_field] = (current + value.replace("\x00", ""))[:maximum]
            return
        if self.mode != "onboarding" or self.focus_field is None:
            return
        replace = self.replace_focused_text
        self.replace_focused_text = False
        if self.focus_field == "setting":
            candidate = ("" if replace else self.setting_text) + value
            candidate = candidate[:350]
            if len(candidate.splitlines()) <= 3:
                self.setting_text = candidate
        elif self.focus_field == "extra":
            self.extra_text = ("" if replace else self.extra_text) + value
            self.extra_text = self.extra_text[:160]
        elif self.focus_field.startswith("player_"):
            index = int(self.focus_field.partition("_")[2])
            current = "" if replace else self.player_names[index]
            self.player_names[index] = (current + value)[:40]

    def delete_text_character(self) -> None:
        if self.mode == "chat" and self.focus_field == "action":
            self.action_text = self.action_text[:-1]
        elif self.mode == "cloud_settings" and self.focus_field in ("narrator_url", "narrator_token"):
            self.pending[self.focus_field] = (
                "" if self.replace_focused_text else self.pending.get(self.focus_field, "")[:-1]
            )
            self.replace_focused_text = False
        elif self.mode == "onboarding" and self.focus_field == "setting":
            self.setting_text = "" if self.replace_focused_text else self.setting_text[:-1]
            self.replace_focused_text = False
        elif self.mode == "onboarding" and self.focus_field == "extra":
            self.extra_text = "" if self.replace_focused_text else self.extra_text[:-1]
            self.replace_focused_text = False
        elif self.mode == "onboarding" and self.focus_field and self.focus_field.startswith("player_"):
            index = int(self.focus_field.partition("_")[2])
            current = self.player_names[index]
            self.player_names[index] = "" if self.replace_focused_text else current[:-1]
            self.replace_focused_text = False

    def paste_clipboard(self) -> None:
        try:
            clipboard = pygame.scrap.get_text()
        except pygame.error:
            self.set_message("cloud_clipboard_error", 5)
            return
        if not clipboard:
            self.set_message("cloud_clipboard_error", 5)
            return
        text = clipboard.replace("\x00", "").strip()
        if not text:
            self.set_message("cloud_clipboard_error", 5)
            return
        self.handle_text_input(text)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.request_quit_confirmation()
            return
        if event.type == pygame.KEYUP and event.key == pygame.K_BACKSPACE:
            self.backspace_held = False
            return
        if self.quit_confirmation:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_n):
                    self.activate_button("quit_cancel")
                elif event.key in (pygame.K_RETURN, pygame.K_y):
                    self.activate_button("quit_confirm")
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                position = self.to_canvas_position(event.pos)
                for key in ("quit_cancel", "quit_confirm"):
                    if self.buttons.get(key, pygame.Rect(0, 0, 0, 0)).collidepoint(position):
                        self.activate_button(key)
                        break
            return
        if event.type == pygame.KEYDOWN:
            if (
                self.mode == "cloud_settings"
                and self.focus_field in ("narrator_url", "narrator_token")
                and event.key == pygame.K_v
                and event.mod & pygame.KMOD_CTRL
            ):
                self.paste_clipboard()
            elif event.key == pygame.K_ESCAPE:
                self.go_back()
                if self.audio_available:
                    self.play_effect(self.ui_sound)
            elif event.key == pygame.K_RETURN:
                if self.mode == "chat":
                    self.submit_action()
                elif self.mode == "onboarding" and self.focus_field == "setting":
                    if len(self.setting_text.splitlines()) < 3:
                        self.setting_text += "\n"
            elif event.key == pygame.K_BACKSPACE:
                self.delete_text_character()
                self.backspace_held = True
                self.backspace_next_repeat = time.monotonic() + 0.4
            elif self.mode == "chat" and event.key == pygame.K_PAGEUP:
                self.chat_scroll = min(self.chat_scroll + 140, max(0, len(self.story_messages) * 145))
            elif self.mode == "chat" and event.key == pygame.K_PAGEDOWN:
                self.chat_scroll = max(0, self.chat_scroll - 140)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.mode == "settings" and event.button == 1:
                position = self.to_canvas_position(event.pos)
                for key, rect in self.sliders.items():
                    if rect.inflate(16, 24).collidepoint(position):
                        self.dragging = key
                        self.update_slider(key, position[0])
                        return
                self.handle_click(position)
            elif event.button == 1:
                self.handle_click(self.to_canvas_position(event.pos))
            elif self.mode == "chat" and event.button in (4, 5):
                self.chat_scroll = max(0, min(
                    self.chat_scroll + (100 if event.button == 4 else -100),
                    max(0, len(self.story_messages) * 145),
                ))
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = None
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.update_slider(self.dragging, self.to_canvas_position(event.pos)[0])
        elif event.type == pygame.TEXTINPUT:
            self.handle_text_input(event.text)

    def to_canvas_position(self, position: tuple[int, int]) -> tuple[int, int]:
        window_width, window_height = self.display.get_size()
        return (
            round(position[0] * WIDTH / window_width),
            round(position[1] * HEIGHT / window_height),
        )

    def update_slider(self, key: str, x: int) -> None:
        rect = self.sliders[key]
        self.pending[key] = max(0.0, min(1.0, (x - rect.x) / rect.width))
        self.apply_audio_settings(self.pending)

    def update_backspace_repeat(self) -> None:
        if not self.backspace_held:
            return
        now = time.monotonic()
        if now < self.backspace_next_repeat:
            return
        self.delete_text_character()
        self.backspace_next_repeat = now + 0.045

    def draw(self) -> None:
        mouse = pygame.mouse.get_pos()
        window_width, window_height = self.display.get_size()
        mouse = (
            round(mouse[0] * WIDTH / window_width),
            round(mouse[1] * HEIGHT / window_height),
        )
        self.buttons.clear()
        self.sliders.clear()
        self.fields.clear()
        if self.mode == "menu":
            self.draw_menu(mouse)
        elif self.mode == "onboarding":
            if self.onboarding_step == 1:
                self.draw_onboarding(mouse)
            else:
                self.draw_character_setup(mouse)
        elif self.mode == "settings":
            self.draw_settings(mouse)
        elif self.mode == "cloud_settings":
            self.draw_cloud_settings(mouse)
        elif self.mode == "chat":
            self.draw_chat(mouse)
        else:
            raise RuntimeError(f"Unknown screen: {self.mode}")
        if self.quit_confirmation:
            self.draw_quit_confirmation(mouse)
        if self.canvas.get_size() == self.display.get_size():
            self.display.blit(self.canvas, (0, 0))
        else:
            pygame.transform.scale(self.canvas, self.display.get_size(), self.display)
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            self.clock.tick(FPS)
            for event in pygame.event.get():
                self.handle_event(event)
            self.update_backspace_repeat()
            self.update_dice_animation()
            self.poll_voice_process()
            self.poll_action_adjudication()
            self.poll_narration()
            self.sync_music()
            self.draw()
        self.stop_voice()
        pygame.quit()


def main() -> None:
    try:
        GameApp().run()
    except pygame.error as error:
        pygame.quit()
        raise SystemExit(f"Could not start Dungeon & Bard: {error}") from error


if __name__ == "__main__":
    main()
