import asyncio
import random
from math import ceil
import discord
import psycopg2
import requests
import treys
from bs4 import BeautifulSoup
from discord import *
from discord.ext import commands, tasks
from discord.ext.commands import has_permissions
from discord.utils import get
import traceback, sys

# somethings were added a lot of time ago, so they are meh.
intents = discord.Intents.default()
intents.members = True
client = commands.Bot(command_prefix='!', intents=intents)
global DEVELOPER
flag = True
# to get the database url: heroku pg:credentials:url -a kingybot
conn = psycopg2.connect(
    host="token",
    database="token",
    user="token",
    password="token")


@tasks.loop(minutes=15, reconnect=True)
async def watermelon_king():
    # this only applies for the hypnotaods guild (the id is that of the guild)
    server = get_guild_named('Vibe Gamers Server (RotMG: HypnoToads Guild)')
    watermelon_role = server.watermelon_role
    # removing the role from the current owner of it
    member = None
    for member in server.guild.members:
        if watermelon_role in member.roles:
            break
    # getting the users and then arranging the list so the one with the most watermelons is the first
    query = "select * from users"
    cursor = conn.cursor()
    cursor.execute(query)
    records = cursor.fetchall()
    records = sorted(records, key=lambda x: (x[3],x[1] + x[2]), reverse=True)
    # finding member of the server with the most watermelons
    for i, record in enumerate(records):
        watermelons_user = server.guild.get_member(int(record[0]))
        if watermelons_user is not None:
            if watermelons_user != member:
                await member.remove_roles(watermelon_role)
                await watermelons_user.add_roles(watermelon_role)
            break


@client.event
async def on_ready():
    await client.change_presence(
        activity=discord.Game(type=discord.ActivityType.playing, name="With yo mama"))
    client.owner_id = 284743911988264971
    global DEVELOPER
    DEVELOPER = client.get_user(client.owner_id)

    if await client.fetch_guild(token) is not None:
        await auto_activate(token)
    if await client.fetch_guild(token) is not None:
        await auto_activate(token)
    print('Logged in as {0} ({0.id})'.format(client.user))
    print('ready!')
    print(discord.__version__)


@watermelon_king.before_loop
async def wait_for_bot():
    # wait for the bot to be ready and then some extra seconds to finish the on_ready method
    await client.wait_until_ready()
    await asyncio.sleep(10)
    print('starting')


def is_owner():
    def predicate(ctx):
        return ctx.author == DEVELOPER

    return commands.check(predicate)


def watermelon_channel():
    async def predicate(ctx):
        if ctx.author == DEVELOPER:
            return True
        channel_to_use = get_guild_named(ctx.guild.name).watermelon_channel
        if ctx.channel == channel_to_use:
            return True
        await ctx.channel.send(f'{ctx.author.mention}, please use the {channel_to_use.mention} channel!',
                               delete_after=5)

    return commands.check(predicate)


class Card:
    def __init__(self, value: int, kind: str):
        self.value = value
        self.kind = kind
        self.string = str(value).__add__(f" of {self.kind}")

    def to_treys_card(self):
        value = self.value
        if value == 1 or value == 14:
            return treys.Card.new("A".__add__(self.kind[0].lower()))
        if value == 10:
            return treys.Card.new("T".__add__(self.kind[0].lower()))
        if value == 11:
            return treys.Card.new("J".__add__(self.kind[0].lower()))
        if value == 12:
            return treys.Card.new("Q".__add__(self.kind[0].lower()))
        if value == 13:
            return treys.Card.new("K".__add__(self.kind[0].lower()))
        elif 2 <= value <= 9:
            return treys.Card.new(str(value).__add__(self.kind[0].lower()))

    def to_discord_send(self):
        value = self.value
        if value == 1 or value == 14:
            value = "A"
        if value == 11:
            value = "J"
        if value == 12:
            value = "Q"
        if value == 13:
            value = "K"

        return f"**{str(value)}**:{self.kind.lower()}:"


class Deck:
    def __init__(self, max_value: int, low_aces=False):
        self.cards = [Card]
        if low_aces:
            for i in range(1, max_value + 1):
                for j in ['Spades', 'Hearts', 'Clubs', 'Diamonds']:
                    self.cards.append(Card(i, j))
        else:
            for i in range(2, max_value + 2):
                for j in ['Spades', 'Hearts', 'Clubs', 'Diamonds']:
                    self.cards.append(Card(i, j))
        self.cards.remove(Card)

    def get_card(self):
        ret = random.choice(self.cards)
        self.cards.remove(ret)
        return ret

    def draw(self, num_to_draw):
        ret = []
        for i in range(num_to_draw):
            ret.append(random.choice(self.cards))
            self.cards.remove(ret[-1])
        return ret


class BlackjackGame:
    def __init__(self):
        self.deck = Deck(13, True)
        self.hand = [self.deck.get_card(), self.deck.get_card()]
        self.dealer_hand = [self.deck.get_card()]

    def get_hand(self):
        return self.hand

    def get_hand_value(self, hand):
        ret = 0
        soft = False
        for i in hand:
            # if ace
            if i.value == 1:
                if ret < 11:
                    ret += 11
                    soft = True
            ret += min(i.value, 10)

        if ret > 21:
            if soft:
                soft = False
                ret -= 10
        return ret

    def get_dealer_hand(self):
        return self.dealer_hand

    def hit(self):
        drawn_card = self.deck.get_card()
        self.hand.append(drawn_card)
        return drawn_card

    def stand(self):
        # drawing only 1 card because we already drew one for the dealer
        drawn_card = self.deck.get_card()
        self.dealer_hand.append(drawn_card)
        player_hand_value = self.get_hand_value(self.hand)
        dealer_hand_value = self.get_hand_value(self.dealer_hand)
        if 21 >= dealer_hand_value >= 17:
            return player_hand_value >= dealer_hand_value
        else:
            while self.get_hand_value(self.dealer_hand) < 17:
                drawn_card = self.deck.get_card()
                self.dealer_hand.append(drawn_card)
            if self.get_hand_value(self.dealer_hand) > 21:
                return True
            return player_hand_value >= self.get_hand_value(self.dealer_hand)


class Reqs:
    def __init__(self, min_stat: int = 0, min_number: int = 0, min_af: int = 0, min_stars: int = 0):
        self.min_stat = min_stat
        self.min_number = min_number
        self.min_af = min_af
        self.min_stars = min_stars


class EmojiList:
    def __init__(self, emojis=None):
        if emojis is None:
            emojis = []
        self.emojis = emojis

    def add_emoji(self, emoji_to_add):
        self.emojis.append(emoji_to_add)


class GuildApplicant:
    def __init__(self, verification_code: str, IGN: str):
        self.verification_code = verification_code
        self.IGN = IGN

    def check_verification(self):
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://www.realmeye.com/player/{self.IGN}"
        page = requests.get(url=url, headers=headers)

        soup = BeautifulSoup(page.content, 'html.parser')
        line1 = ""
        line2 = ""
        line3 = ""

        try:
            line1 = soup.find_all(class_='line1 description-line')[0].text
        except:
            pass
        try:
            line2 = soup.find_all(class_='line2 description-line')[0].text
        except:
            pass
        try:
            line3 = soup.find_all(class_='line3 description-line')[0].text
        except:
            pass
        description_string = ""
        if line1 != "":
            description_string = description_string.__add__(line1)
            description_string = description_string.__add__("\n")
        if line2 != "":
            description_string = description_string.__add__(line2)
            description_string = description_string.__add__("\n")
        if line3 != "":
            description_string = description_string.__add__(line3)

        if str(self.verification_code) in description_string:
            return True
        else:
            return False


class NewPoll:
    def __init__(self, poll_channel, poll_author, question=""):
        self.poll_channel = poll_channel
        self.poll_author = poll_author
        self.question = question
        self.editable = True

    def set_question(self, question):
        self.question = question


class discord_server:
    def __init__(self, guild_name: str):
        self.guild = get(client.guilds, name=guild_name)
        self.reqs = Reqs(0, 0, 0, 0)
        self.name = self.guild.name
        self.verify_channel = guild_name
        self.welcome_msg = ''
        self.follower_role = None
        self.newcomers_log_channel = None
        self.wannabe_role = None
        self.recruiter_channel = None
        self.recruiter_role = None
        self.mod_channel = None
        self.mod_role = None
        self.member_role = None
        self.watermelon_channel = None
        self.watermelon_role = None
        self.polls = []
        self.applicants = []

    def set(self, name_of_val, val_of_name):
        is_channel = name_of_val.split("_")[-1] == 'channel'
        str = f"self.{name_of_val} = get(self.guild.{'channels' if is_channel else 'roles'}, name=val_of_name)\nprint(name_of_val,val_of_name)"
        exec(str)

    def set_reqs(self, min_stat: int = 0, min_number: int = 0, min_af: int = 0, min_stars: int = 0):
        self.reqs = Reqs(min_stat, min_number, min_af, min_stars)

    def set_welcome_msg(self, msg):
        self.welcome_msg = msg


guilds = [discord_server]


@client.event
async def on_member_join(mem):
    await check_dm(mem)
    await mem.dm_channel.send(get_guild_named(mem.guild.name).welcome_msg)


@has_permissions(manage_roles=True)
@client.command(pass_context=True)
async def activate(ctx):
    global flag
    global guilds
    if flag:
        guilds = [discord_server(ctx.guild.name)]
        flag = False
    elif get_guild_named(ctx.guild.name) in guilds:
        await ctx.channel.send('The bot is already activated in this guild!')
        return
    else:
        guilds.append(discord_server(ctx.guild.name))
    await ctx.channel.send(f'Bot added to {ctx.guild.name}!')


async def auto_activate(guild_id: int = None):
    global guilds
	server1 = await client.fetch_guild(guild_id)
    if guild_id == token:
        # hypno server
        global flag
        flag = False
        guilds = [discord_server(server1.name)]
        server = get_guild_named(server1.name)
        server.set('mod_role', 'Mods')
        server.set('verify_channel', 'verify-here')
        server.set_welcome_msg(
            f"Welcome to the Vibe Gamers Server!."
            f"\n\nTo verify please follow the instructions in {server.verify_channel.mention}."
            f"\n\nIf you wish to join the in-game guild please use !apply."
            f"\n\nAny issues use !mod_mail followed by your message.")
        server.set('follower_role', 'Followers')
        server.set('wannabe_role', 'Tadpoles')
        server.set('newcomers_log_channel', 'tadpole-information')
        server.set('recruiter_channel', 'tadpole-information')
        server.set('recruiter_role', 'Officer')
        server.set('mod_channel', 'mod-mail')
        server.set_reqs(8, 3, 10000, 65)
        server.set('member_role', 'Members')
        server.set('watermelon_channel', 'dank-memer')
        server.set('watermelon_role', 'watermelon king')
        await check_dm(DEVELOPER)
        await DEVELOPER.dm_channel.send(f'Server activated with {server1.name} special presets!')
        return
    if guild_id == token:
        # my own server
        guilds.append(discord_server(server1.name))
        server = get_guild_named(server1.name)
        server.set('watermelon_channel', "general")
        server.set('verify_channel', "general")


@has_permissions(manage_nicknames=True)
@client.command(pass_context=True)
async def delete(ctx, number: int = 1):
    number = int(number + 1)
    await ctx.channel.purge(limit=number)


def get_guild_named(name):
    global guilds
    for i in guilds:
        if i.name == name:
            return i
    guilds.append(discord_server(name))
    return guilds[-1]


async def check_dm(check_me):
    if check_me.dm_channel is None:
        await check_me.create_dm()


@client.command(pass_context=True)
async def mod_mail(ctx):
    if ctx.message is None:
        await ctx.channel.send('What? No message?')
    channel_to_send = get_guild_named(ctx.guild.name).mod_channel
    await DEVELOPER.send(f'...................\n{ctx.message.content[10:]}')
    await DEVELOPER.send(f'Mod mail sent by {ctx.message.author.mention}')
    if channel_to_send:
        await check_dm(ctx.author)
        await ctx.author.dm_channel.send('Message sent!')
        await channel_to_send.send(f'...................\n{ctx.message.content[10:]}')
        await channel_to_send.send(f'Sent by {ctx.message.author.mention}')
    await ctx.message.delete()


@client.command(pass_context=True)
async def dev(ctx):
    if ctx.message is None:
        await ctx.channel.send('What? No message?')
    await DEVELOPER.send(ctx.message.content[5:])
    await check_dm(ctx.author)
    await ctx.author.dm_channel.send(f'Message sent!\nContent: "{ctx.message.content[5:]}"')
    name = ctx.author.nick
    if not name:
        name = ctx.author.name
    await DEVELOPER.send(
        f'Dev mail sent by {ctx.message.author.mention} (nick name: {name}), server: {ctx.guild}')
    await ctx.message.delete()


@client.command(pass_context=True)
async def ok(ctx):
    await ctx.message.channel.send('Boomer!')


@client.command(pass_context=True)
async def music(ctx):
    await ctx.message.channel.send('I love music!')


@client.command(pass_context=True)
async def white(ctx):
    nickname = listToString(ctx.message.content.split(" ")[1:], " ")
    mem = ctx.guild.get_member_named(nickname)
    if nickname is None:
        await ctx.message.channel.send('Who got it tho??.\nThe correct syntax is !white <IGN>.')
    elif mem is None:
        await ctx.message.channel.send(f"bruh\n{nickname} isn't even in the guild -_-")
    else:
        if mem.nick is None:
            responses = [f'{nickname} is one lucky bastard!',
                         f'{nickname} i got one of these yesterday lol xD',
                         f'{nickname} jealous? :)', f'GZ {nickname}!',
                         f'Bruh {nickname} gib it',
                         f'Is {nickname} using hax?',
                         f"{ctx.author.mention} it's over-rated anyway",
                         f"Nice character, {nickname}!"]
        else:
            responses = [f'{mem.nick} is one lucky bastard!', f'{mem.nick} i got one of these yesterday lol xD',
                         f'{ctx.message.author.mention} jealous? :)', f'GZ {mem.nick}!', f'Bruh {mem.nick} gib it',
                         f'Is {mem.nick} using hax?', f"{ctx.message.author.mention} it's over-rated anyway",
                         f"Nice character, {mem.nick}!"]
        await ctx.message.channel.send(responses[random.randrange(len(responses))])


@client.command(pass_context=True)
async def verify(ctx, IGN=None, timezone=None):
    server = get_guild_named(ctx.guild.name)
    role_to_add = server.follower_role
    writer = ctx.message.author
    await check_dm(writer)
    await ctx.message.delete()

    if ctx.channel != server.verify_channel:
        await writer.dm_channel.send(f'Please use the {server.verify_channel.mention} channel!')
        return

    if IGN is None or timezone is None:
        await writer.dm_channel.send(
            f'the correct syntax is: !verify <IGN> <timezone>. Example: !verify Kingyairba gmt+3. ')
        return
    elif role_to_add in writer.roles:
        await writer.dm_channel.send(
            f'You already have the {role_to_add} role. Use the !mod_mail <message> command to get help.')
        return
    await writer.dm_channel.send(
        f'You got the {role_to_add} role!')
    if server.wannabe_role:
        await writer.dm_channel.send(
            f'If you want to join the guild, use !apply in '
            f'{server.verify_channel.mention} and wait for a DM from staff.')
    if server.student_role:
        await writer.dm_channel.send(
            f'To become a student, use !verify_role student in {server.verify_channel.mention}.')
    await writer.edit(nick=IGN)
    await writer.add_roles(role_to_add)
    channel_to_send = get_guild_named(ctx.guild.name).newcomers_log_channel
    if channel_to_send:
        await channel_to_send.send(
            f"..........................\nIGN: {writer.mention}\ntime zone: {timezone}\n"
            f"rank: {role_to_add}\nRealmeye:https://www.realmeye.com/player/{IGN}")


@client.command(pass_context=True)
async def member(ctx, give_to: str = None, *, member_info: str):
    member_guild = get_guild_named(ctx.guild.name)
    role_to_add = member_guild.member_role
    new_member = ctx.guild.get_member_named(give_to)
    if member_guild.recruiter_role not in ctx.author.roles:
        await ctx.channel.send(f"{ctx.author.mention}, only {member_guild.recruiter_role} can use this command!")
        await ctx.message.delete()
        return
    if not new_member:
        await ctx.channel.send(f"bruh\n{give_to} isn't even in the guild!")
        return
    if role_to_add in new_member.roles:
        await ctx.channel.send(f"{ctx.author.mention},{new_member.mention} is already a member!")
        return

    if give_to is None:
        await ctx.channel.send(f"{ctx.author.mention}, who do you want to member?")
        return
    if member_guild.follower_role not in new_member.roles:
        await ctx.channel.send(f"{ctx.author.mention}, {give_to} isn't a {member_guild.follower_role} yet!")
        return
    try:
        await new_member.add_roles(member_guild.member_role)
        await ctx.channel.send(
            f"{ctx.author.mention}, {new_member.mention} was given the {member_guild.member_role} role!")
        await check_dm(new_member)
        await new_member.dm_channel.send(f'{new_member.mention}, welcome!')
        time_zone, notes, circom = member_info.split(':')
        await member_guild.newcomers_log_channel.send(
            f".....................\nIGN:{new_member.mention}\nRank:{member_guild.member_role}\nTime zone: {time_zone}"
            f"\nNotes: {notes}\nSpecial circum: {circom}\nWas added by: {ctx.author.nick}")
    except:
        await ctx.channel.send(
            f"{ctx.author.mention},an error accrued!")


def get_pet_data(IGN):
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://www.realmeye.com/pets-of/{IGN}"
    page = requests.get(url=url, headers=headers)

    soup = BeautifulSoup(page.content, 'html.parser')

    pet_results = soup.find(class_='table table-striped tablesorter')

    pet_subjects, pets = pet_results

    pets_list = []
    pet_data = ""
    for pet in pets:
        pets_list.append(pet.find_all('td'))
    best_pet = pets_list[0]
    random_data, name, rarity, pet_family, place, ability1, ability1_level, \
    ability2, ability2_level, ability3, ability3_level, max_level = best_pet

    pet_data = pet_data.__add__(f"Rarity: {rarity.text}\n")
    pet_data = pet_data.__add__(f"Family: {pet_family.text}\n")
    if ability1_level.text != "":
        pet_data = pet_data.__add__(f"{ability1.text} Level: {ability1_level.text}\n")
    if ability2_level.text != "":
        pet_data = pet_data.__add__(f"{ability2.text} Level: {ability2_level.text}\n")
    if ability3_level.text != "":
        pet_data = pet_data.__add__(f"{ability3.text} Level: {ability3_level.text}\n")
    pet_data = pet_data.__add__(f"Max ability level: {max_level.text}\n")

    embed = discord.Embed(title=f"{IGN}'s best pet's information:", description=pet_data, color=discord.Color.blue())
    return embed


"""            char_data = stats.pop(0).text
            class_name = stats.pop(0).text
            level = stats.pop(0).text
            CQC = stats.pop(0).text
            fame = stats.pop(0).text"""
"""            XP = stats.pop(0).text
            place = stats.pop(0).text
            equipment = stats.pop(0).text
            out_of_eight = stats.pop(0).text"""


# noinspection PyPep8Naming
@has_permissions(manage_nicknames=True)
@client.command(pass_context=True)
async def get_data(ctx, IGN: str, channel_name: str = ""):
    ret = []
    member_guild = get_guild_named(ctx.guild.name)
    guild_reqs = member_guild.reqs
    headers = {"User-Agent": "Mozilla/5.0"}
    send_to_channel = get(ctx.guild.channels, name=channel_name)
    if channel_name == "":
        send_to_channel = ctx.channel
    url = f"https://www.realmeye.com/player/{IGN}"
    page = requests.get(url=url, headers=headers)

    soup = BeautifulSoup(page.content, 'html.parser')

    star_results = soup.find_all('div', class_='star-container')[0]
    star_amount = int(star_results.text)

    char_results = soup.find(class_='table table-striped tablesorter')

    try:
        subjects, chars = char_results
    except:
        await ctx.channel.send(
            f'{ctx.author.mention}, something went wrong. Please contact the developer and tell him what heppened.')
        return

    af = 0
    reqs = 0
    char_string = ""
    wrong = False
    # header = [ 'Level', '?/8','Class']
    # looping through the chars
    # equipment_links = []
    for char in chars:
        stats = char.find_all('td')
        try:
            # if pet:
            # stats.pop(0)
            # equipment_links = equipment_links.append([])
            stats.pop(0)
            char_data, class_name, level, CQC, fame, XP, place, equipment, out_of_eight = stats[:9]
            '''            char_data = stats.pop(0)
            class_name= stats.pop(0)
            level= stats.pop(0)
            CQC= stats.pop(0)
            fame= stats.pop(0)
            XP= stats.pop(0)
            place= stats.pop(0)
            equipment= stats.pop(0)
            out_of_eight= stats.pop(0)'''

            char_data, class_name, level, CQC, fame, XP, place, out_of_eight = char_data.text, class_name.text, level.text, CQC.text, fame.text, XP.text, place.text, \
                                                                               out_of_eight.text.strip().split('/')[0]
            # for i in equipment:
            #   the_a = i.find('a')
            #   link = 'https://www.realmeye.com'.__add__(the_a['href'])
            #   name_list = the_a.find('span')['title'].split(' ')[:-1]
            #   name = ''
            #   for i in name_list:
            #       name = name.__add__(' ')
            #       name = name.__add__(i)
            #   name = name.lstrip()
            #   name = name.rstrip()
            #   image_link = get_item_img(link, name)
            #   if name != '':
            #       equipment_links[-1].append(image_link)

            af += int(fame)

        except Exception as e:
            print(e)
            wrong = True
        else:
            try:
                if out_of_eight != '?':
                    if int(out_of_eight) >= guild_reqs.min_stat:
                        reqs += 1
                string = f"Level {level} {class_name}, {out_of_eight} with {fame} base fame\n"
                char_string = char_string.__add__(string)
            except Exception as e:
                print(e)
                wrong = True

    if wrong:
        char_string = 'oops, something went wrong, something in the character checking loop, with the popping thingy.'
    embed1 = discord.Embed(title=f"{IGN}'s characters:", description=char_string, color=discord.Color.blue())
    char_string = ""
    color = discord.Color.green()
    char_string = char_string.__add__(f'{IGN} has {af} alive fame, and {star_amount} stars.\n')
    try:
        if af >= guild_reqs.min_af and reqs >= guild_reqs.min_number and star_amount >= guild_reqs.min_stars:
            char_string = char_string.__add__(f'{IGN} meets requirements.\n')
        else:
            char_string = char_string.__add__(f'{IGN} does not meet requirements.\n')
            color = discord.Color.red()
    except:
        char_string = 'OOPS! Something went wrong! Please use the !mod_mail <msg> command to report the bug.'
    embed2 = discord.Embed(title=f"{IGN}'s account info:", description=char_string, color=color)
    embed2.add_field(name=f"{IGN}'s realmeye:", value=url)
    ret.append(embed1)
    ret.append(embed2)

    try:
        embed3 = get_pet_data(IGN)
        ret.append(embed3)
    except:
        embed3 = discord.Embed(title=f"{IGN}'s best pet's information:",
                               description=f"{IGN}'s pet yard page is private", color=discord.Color.red())

    await send_to_channel.send(embed=embed1)
    if channel_name == "":
        await send_to_channel.send(embed=embed3)
    await send_to_channel.send(embed=embed2)

    return embed1, embed2


def get_item_img(URL, name):
    headers = {"User-Agent": "Mozilla/5.0"}
    page = requests.get(url=URL, headers=headers)

    soup = BeautifulSoup(page.content, 'html.parser')
    images = soup.find('img', alt=name)
    print(images['src'][2:])
    # for i in images:
    #   links = links.append(i['src'][2:0])
    #   print(i['src'][2:])
    return images


def generate_code():
    return random.randrange(1000, 2000)


def remove_speciel_keys(string):
    use = ""
    for character in string:

        if character.isalnum():
            use += character
    return use.lower()


async def check_dm_command(ctx):
    await check_dm(ctx.author)
    if ctx.channel == ctx.author.dm_channel:
        await ctx.author.send(f"{ctx.author.mention}, command {apply} can't be used here!", delete_after=5)
        return False
    return True


@client.command(pass_context=True)
async def apply(ctx, ign: str = None):
    await ctx.message.delete()
    server = get_guild_named(ctx.guild.name)
    await check_dm(ctx.author)
    rolee = server.follower_role
    writer = ctx.author
    role1 = server.wannabe_role
    channel_var = server.verify_channel
    if not rolee or not channel_var:
        await writer.dm_channel.send(
            f'{writer.mention} something went wrong... please use the !mod_mail <message> and tell us what happened!')
        return

    if ctx.channel != server.verify_channel:
        await writer.dm_channel.send(f'Please use the {server.verify_channel.mention} channel!')
        return

    if rolee not in writer.roles:
        await writer.dm_channel.send(
            f'{writer.mention} please use the !verify <ign> <timezone> command first')
        return
    if role1 in writer.roles and role1 != rolee:
        await writer.dm_channel.send(f'{writer.mention}, you already have the {server.wannabe_role} role!')
        return

    if ign is None:
        ign = ctx.author.name
        if ctx.author.nick:
            ign = ctx.author.nick
        ign = remove_speciel_keys(ign)
        for i in server.applicants:
            if i.IGN == ign:
                server.applicants.remove(i)
                break
        code = generate_code()
        server.applicants.append(GuildApplicant(str(code), ign))
        send = f"Thank you for verifying your account!\nYour verification code is: **{str(code)}**." \
               f"\nPlace the verification code in any of your realmeye description bars." \
               f"\nOnce you have saved the code to your realmeye description type !apply [realmeye name]." \
               f"\nYou can verify in the {server.verify_channel.mention} channel! Realm eye names are NOT " \
               f"case-sensitive! "
        await ctx.author.dm_channel.send(send)

    else:
        applicant = None
        ign = ign.lower()
        for i in server.applicants:
            if i.IGN == ign:
                applicant = i
        if applicant is None:
            await ctx.author.dm_channel.send(
                f'Please use the !apply command first in {server.verify_channel.mention}. After that use !apply <ign> '
                f'(in the same {server.verify_channel.mention} channe).')
            return False

        verified = applicant.check_verification()
        if not verified:
            await writer.dm_channel.send(
                f"The verification process failed. If you think a problem accrued, please contact staff.")
            return

        if ctx.channel == channel_var and verified:
            use = ""
            if role1 not in writer.roles:
                await writer.add_roles(role1)
                # await writer.dm_channel.send(
                #   f'{writer.mention}, u got the {role1.name} role!')
            channel_var = server.recruiter_channel
            rolee = server.recruiter_role
            if channel_var and rolee:
                await channel_var.send(f'........{rolee.mention}........')
                await channel_var.send(f'New wannabe: {writer.mention}')
                if writer.nick is not None:
                    for character in writer.nick:
                        if character.isalnum():
                            use += character
                else:
                    for character in ctx.author.name:

                        if character.isalnum():
                            use += character
                await get_data(ctx, use, channel_var.name)

            # the bot interview question
            msg_ = await writer.send(
                embed=discord.Embed(title='Guild interview', description='Are you ready to have a text '
                                                                         'interview with me (the bot) '
                                                                         'for the guild? The answers '
                                                                         'will be sent to staff. ('
                                                                         'react with the ✅ if you are '
                                                                         'ready, you have 60 seconds '
                                                                         'to do so).',
                                    color=discord.Color.blue()))
            await msg_.add_reaction('✅')

            def check_reaction(reaction_, user_):
                return reaction_.emoji == '✅' and reaction_.message.channel == writer.dm_channel and reaction_.count == 2 and user_

            try:
                await client.wait_for('reaction_Add', check=check_reaction, timeout=60.0)
            except asyncio.TimeoutError:
                await msg_.edit(embed=discord.Embed(title='No reaction detected', color=discord.Color.red()))
                await channel_var.send(
                    embed=discord.Embed(title=f"Looks like {use} didn't wanna share... ", color=discord.Color.blue()))
            else:

                questions = ['Is there Is there anything you want to tell about yourself? realm - wise or not',
                             'Do you have experience in end-game dungeons?', 'How did you find out about this discord?']

                def check_message(m):
                    return m.author == writer and m.channel == writer.dm_channel

                key = random.randrange(10000000)
                responses = [key]
                for i, question in enumerate(questions):
                    await msg_.edit(
                        embed=discord.Embed(title='Guild Interview', description=question, color=discord.Color.blue()))
                    msg = ''
                    try:
                        msg = await client.wait_for('message', check=check_message)
                    except:
                        await msg_.edit(
                            embed=discord.Embed(title='Guild Interview',
                                                description='Something went wrong.... please contact staff!',
                                                color=discord.Color.red()))
                        msg = 'oops, something went wrong in the interview'
                    finally:

                        if responses[0] == key:
                            responses = [msg.content]
                        else:
                            responses.append(msg.content)

                else:
                    await msg_.edit(embed=discord.Embed(title='Guild interview',
                                                        description=f'Your responses were sent to staff! You will be '
                                                                    f'contacted shortly. For any questions, '
                                                                    f'use the !mod_mail <message> command (not here '
                                                                    f'tho, use it in the server).',
                                                        color=discord.Color.blue()))
                    interview_responses_embed = discord.Embed(title=f'Interview with {use}:',
                                                              color=discord.Color.blue())
                    for i, (question, response) in enumerate(zip(questions, responses)):
                        interview_responses_embed.add_field(name=question, value=response, inline=False)

                    await channel_var.send(
                        embed=interview_responses_embed)
            channel_var = server.newcomers_log_channel
            if channel_var:
                await channel_var.send(f'{writer.mention} got the {server.wannabe_role} role!')


@has_permissions(manage_nicknames=True)
@client.command(pass_context=True)
async def poll(ctx, command: str = "create", target_channel=""):
    await ctx.message.delete(delay=3)
    server = get_guild_named(ctx.guild.name)
    send_to_channel = ctx.channel
    if target_channel != "":
        send_to_channel = get(ctx.guild.channels, name=target_channel)
    if command == "create":
        created_poll = NewPoll(ctx.channel, ctx.author)
        server.polls.append(created_poll)
        await ctx.channel.send(f'{ctx.author.mention}, please type the question for the poll you just created('
                               f'you have a minute to do so)', delete_after=5)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await client.wait_for('message', check=check, timeout=60.0)
        except asyncio.TimeoutError:
            await ctx.channel.send(
                f'{ctx.author.mention}, no question was sent so poll creation was aborted.', delete_after=5)
        else:
            created_poll.set_question(msg.content)
            await ctx.channel.send(
                f'{ctx.author.mention}, poll created! use **!poll send <channel name>** to send it!', delete_after=5)

    if command == "send":
        embed1 = None
        for i in server.polls:
            if i.poll_author == ctx.author:
                embed1 = discord.Embed(title=i.question, description="", color=discord.Color.blue())
                server.polls.remove(i)
                break
        if not embed1:
            await ctx.channel.send(f"{ctx.author.mention}, please use **!poll create** first!", delete_after=5)
            return
        msg = await send_to_channel.send(embed=embed1)

        await msg.add_reaction("✅")
        await msg.add_reaction("❎")


@has_permissions(manage_nicknames=True)
@client.command(pass_context=True)
async def DM(ctx, nickname: str = None, *, msg):
    await ctx.message.delete()
    if not nickname:
        await ctx.channel.send(f'{ctx.author.mention}, who do you want to send it to?', delete_after=3)

    mem = ctx.guild.get_member_named(nickname)
    if not mem:
        await ctx.channel.send(f'{ctx.author.mention}, {nickname} was not found!', delete_after=3)
    await check_dm(mem)
    anonymous = msg.split(" ")[0]
    if anonymous == 'f':
        temp = msg.split(" ")[1:]
        msg = ""
        for i in temp:
            msg = msg.__add__(i)
            msg = msg.__add__(" ")
    await mem.send(f"{msg}")
    if anonymous != 'f':
        await mem.send(f"sent by: {ctx.author.mention}")


@has_permissions(manage_nicknames=True)
@client.command(pass_context=True)
async def with_role(ctx, *, role_name):
    role_to_search = get(ctx.guild.roles, name=role_name)
    if role_to_search is None:
        await ctx.channel.send(f'There is no "{role_name}" role on this server!')
        return
    members = []
    temp = ''
    for member_with_role in ctx.message.guild.members:
        if role_to_search in member_with_role.roles:
            members.append(member_with_role)
            name = member_with_role.name
            if member_with_role.nick:
                name = member_with_role.nick
            temp = temp.__add__(f'{member_with_role.mention}({name}), ')
    if temp == '':
        await ctx.channel.send(f"Nobody has the role '{role_name}'")
        return
    temp = temp[:-2]
    members_embed = discord.Embed(title=f'Members with the {role_name} role:', description=temp,
                                  color=discord.Color.blurple())
    try:
        await ctx.channel.send(embed=members_embed)
    except:
        str_list = temp[:2000].split(' ')[:-1]
        temp = ''
        for i in str_list:
            temp = temp.__add__(i)
            temp = temp.__add__(' ')
        temp = temp[:-2]
        members_embed = discord.Embed(title=f'Members with the "{role_name}" role:', description=temp,
                                      color=discord.Color.blurple())
        members_embed.add_field(name='oops!',
                                value=f"Too many people have the '{role_name}' role, so i'll just show the first {len(str_list)}...")
        await ctx.channel.send(embed=members_embed)
    return members_embed


def get_name(user_to_get):
    name = user_to_get.name
    try:
        if user_to_get.nick:
            name = user_to_get.nick
    except:
        pass
    return name


@client.command(pass_context=True)
@watermelon_channel()
async def blackjack(ctx):
    num = get_watermelon_num(ctx)
    # playing with num because I wanted to incearese the EV so it will be more fun
    reward = 0
    # up until here everything was just making sure everything is ok(the right channel) and getting the server.
    game = BlackjackGame()
    user_hand = game.get_hand()
    stop = False

    def get_hand_str(hand):
        ret = ""
        for card_in_hand in hand:
            ret = ret.__add__(
                card_in_hand.to_discord_send())
        return ret

    # creating the first Embed!
    game_info = get_hand_str(user_hand).__add__(f"\nTotal:**{game.get_hand_value(game.hand)}**")
    dealer_hand_info = get_hand_str(game.get_dealer_hand()).__add__(
        f"\nTotal:**{game.get_hand_value(game.get_dealer_hand())}**")
    name = get_name(ctx.author)
    embed = discord.Embed(title=f"{name}'s Blackjack game: playing on **{num}** watermelons.",
                          color=discord.Color.blue(),
                          description="react with ✅ to hit, and with ❎ to stand. If you "
                                      "want an ace to count as a 1 and not as 11, just hit and the game will "
                                      "continue.")
    embed.add_field(name=f"{name}'s hand", value=game_info)
    embed.add_field(name=f"Dealer's hand", value=dealer_hand_info)

    # handleling the lucky bastrards who got 21 with the first two cards.
    if game.get_hand_value(game.hand) == 21:
        reward = 3 * num

        embed.add_field(name=f"You won **{reward}** watermelons!",
                        value="Winner winner chicken dinner! True Blackjack!", inline=False)
        embed.add_field(name="react with the ✅ to play again!", value="10 seconds timeout!",
                        inline=False)
        embed.colour = discord.Color.green()
        stop = True

    game_msg = await ctx.channel.send(embed=embed)
    await game_msg.add_reaction("✅")
    await game_msg.add_reaction("❎")

    def reaction_check(reaction__, user_):
        return user_ == ctx.author and (reaction__.emoji == "✅" or reaction__.emoji == "❎")

    win = False
    # while the game is still going:
    while not stop:
        # wait for reaction, v for hit, x for stand
        try:
            reaction_, reactor = await client.wait_for('reaction_add', check=reaction_check)
        except asyncio.TimeoutError:
            await game_msg.edit(
                embed=discord.Embed(title="No reaction detected, aborting game.", color=discord.Color.red()))
        else:
            try:
                await reaction_.remove(ctx.author)
            except:
                pass
            # if v, hit. after hit: check if lost and if won.
            embed = game_msg.embeds[0]
            if reaction_.emoji == "✅":
                game.hit()
            elif reaction_.emoji == "❎":
                # stand: check who won
                stop = True
                win = game.stand()

            dealer_hand_info = get_hand_str(game.get_dealer_hand()).__add__(
                f"\nTotal:**{game.get_hand_value(game.dealer_hand)}**")
            hand_value = game.get_hand_value(game.hand)
            game_info = get_hand_str(user_hand).__add__(f"\nTotal:**{hand_value}**")
            embed.set_field_at(0, name=f"{name}'s hand", value=game_info)
            embed.set_field_at(1, name=f"Dealer's hand", value=dealer_hand_info)
            if hand_value == 21:
                stop = True
                win = True
            elif hand_value > 21:
                win = False
                stop = True
            if stop:
                reward = int(num * 1.5) if win else -num
                embed.add_field(name=f"You won **{reward}** watermelons!" if win else "You lost!",
                                value="Winner winner chicken dinner!" if win else "Better luck next time!",
                                inline=False)
                embed.add_field(name="react with the ✅ to play again!", value="10 seconds timeout!",
                                inline=False)
                embed.colour = discord.Color.green() if win else discord.Color.red()
            await game_msg.edit(embed=embed)
    try:
        # giving the reward to the user
        update_table_with(ctx.author, watermelons=reward if win is False else get_amount(ctx.author, reward))
        # waiting for another v reaction to start another game
        await game_msg.clear_reaction("❎")
        reaction_, reactor = await client.wait_for('reaction_add', check=reaction_check, timeout=10.0)
    except asyncio.TimeoutError:
        embed = discord.Embed(title="No reaction detected, aborting game.", color=discord.Color.blue())
        embed.add_field(name=f"{name}'s hand", value=game_info)
        embed.add_field(name=f"Dealer's hand", value=dealer_hand_info)
        await game_msg.edit(embed=embed)
        await game_msg.clear_reactions()

    else:
        if reaction_.emoji == "✅":
            # got the v reaction, starting another game! good luck and remember: the house always wins.
            await game_msg.delete()
            await blackjack(ctx)


def create_watermelon_user(user_to_create: discord.member):
    id = str(user_to_create.id)
    watermelons = 100
    bank_watermelons = 0
    level = 0
    cursor = conn.cursor()
    try:

        postgres_query = " INSERT INTO users (id,watermelons,bank,level) VALUES (%s,%s,%s,%s)"
        record_to_insert = (id, watermelons, bank_watermelons, level)
        cursor.execute(postgres_query, record_to_insert)
        conn.commit()
        count = cursor.rowcount
        print(count, "Record inserted successfully into mobile table")
    except (Exception, psycopg2.Error) as error:
        if conn:
            print("Failed to insert record into mobile table", error)
    finally:
        cursor.close()


def get_watermelon_user(user_to_get: discord.client):
    id = str(user_to_get.id)
    cursor = conn.cursor()
    try:
        postgres_query = "select * from users where id = %s"
        parms = (id,)
        cursor.execute(postgres_query, parms)
        records = cursor.fetchone()
        cursor.close()
        if records:
            return records
        else:
            create_watermelon_user(user_to_get)
            return get_watermelon_user(user_to_get)
    except (Exception, psycopg2.Error) as error:
        if conn:
            print("Error fetching data from PostgreSQL table", error)


def update_table_with(user_to_change: discord.client, **parms):
    cursor = conn.cursor()
    try:
        watermelon_user = dict(zip(['id', 'watermelons', 'bank', 'level'], get_watermelon_user(user_to_change)))
        # adding the current data so we so it won't be overwritten (for example, if we are adding 10 watermelons to a user with 10 watermelons, we need to add the current watermelons to the amount we want to add because an update query just overwrites)
        # and completing the query string
        # this is for the variables
        update_str = ""
        # this is for the values
        vals = []
        for i, param in enumerate(parms):
            update_str += f"{param} = %s,"
            vals.append(f"{parms[param] + watermelon_user[param]}")
        update_str = update_str[:-1]
        vals.append(str(user_to_change.id))
        # building the query
        postgres_query = f"UPDATE users SET {update_str} where id = %s"
        # executing and saving
        cursor.execute(postgres_query, vals)
        conn.commit()
        cursor.close()

    except (Exception, psycopg2.Error) as error:
        print("Error in update operation", error)


@commands.cooldown(1, 20, commands.BucketType.user)
@client.command(pass_context=True)
@watermelon_channel()
async def claim(ctx):
    amount = get_bonuses(ctx.author)[1] + 35
    update_table_with(ctx.author, watermelons=amount)
    await ctx.channel.send(f'{ctx.author.mention}, you got **{amount}** watermelons!')


@client.command(pass_context=True)
@watermelon_channel()
async def bank(ctx):
    num = get_watermelon_num(ctx)
    update_table_with(ctx.author, watermelons=-num, bank=num)
    await ctx.channel.send(f"{ctx.author.mention}, You banked **{num}** watermelons!")


@client.command(pass_context=True)
@watermelon_channel()
async def withdraw(ctx):
    num = get_watermelon_num(ctx, False)
    update_table_with(ctx.author, watermelons=num, bank=-num)
    await ctx.channel.send(f"{ctx.author.mention}, You withdrew **{num}** watermelons!")


@client.command(pass_context=True)
@watermelon_channel()
async def show(ctx):
    try:
        watermelons, bank_watermelons, level = get_watermelon_user(ctx.author)[1:]
        level_info = get_level_data(level)
        await ctx.channel.send(
            f"{ctx.author.mention}, you are level **{level}**, you have **{watermelons}** watermelons, and **{bank_watermelons}** watermelons in the bank!. "
            f"Level up cost: **{level_info[0]}**. Watermelon gain multiplier: **{1 + level_info[1]}**. Claim bonus: **{level_info[2]}**")
    except:
        await ctx.channel.send(f"{ctx.author.mention}, oops! Something went wrong!")


@client.command(pass_context=True)
@watermelon_channel()
async def peak(ctx, user_name):
    try:
        mem = ctx.guild.get_member_named(user_name)
        watermelons, bank_watermelons,level = get_watermelon_user(mem)[1:]
        await ctx.channel.send(
            f"{ctx.author.mention} is level **{level}**, **{user_name}** has **{watermelons}** watermelons, and **{bank_watermelons}** watermelons in the bank!")
    except:
        await ctx.channel.send(f"{ctx.author.mention}, oops! Something went wrong!")


@commands.cooldown(1, 7, commands.BucketType.user)
@client.command(pass_context=True)
@watermelon_channel()
async def gamble(ctx):
    num = get_watermelon_num(ctx)
    number = random.randrange(0, 100)
    if number >= 33:
        num = get_amount(ctx.author, num)
        await ctx.channel.send(f'{ctx.author.mention} you won **{num}** watermelons!')
        update_table_with(ctx.author, watermelons=num)
    else:
        await ctx.channel.send(f'{ctx.author.mention} you lost **{num}** watermelons...')
        update_table_with(ctx.author, watermelons=-num)


@client.command(pass_context=True)
@watermelon_channel()
async def steal(ctx):
    num = get_watermelon_num(ctx)
    steal_from = listToString(ctx.message.content.split(" ")[2:], " ")
    watermelons = get_watermelon_user(ctx.author)[1]
    if steal_from == get_name(ctx.author):
        if watermelons > 2:
            await ctx.channel.send(
                "Imagine trying to steal from yourself! LOL. You were fined a watermelon for stupidity")
            update_table_with(ctx.author, watermelons=-1)
        else:
            ctx.channel.send("Imagine trying to steal from yourself! LOL.")
        return

    if steal_from is None:
        await ctx.channel.send('Who do you want to steal from?')
        return

    elif watermelons - int(ceil(num / 3)) < 0:
        await ctx.channel.send(
            f"{ctx.author.mention}, Cannot steal! (no more watermelons). If u can't pay the fee (the number to steal / 3) don't try!")
        return
    else:
        mem = ctx.guild.get_member_named(steal_from)
        if not mem:
            await ctx.channel.send(f"bruh\n{steal_from} isn't even in the guild...")
            return
        user_steal_from = get_watermelon_user(mem)
        if user_steal_from[1] < num:
            if watermelons > 1:
                await ctx.channel.send(
                    f'You see that {steal_from} has less watermelons than you wanted to steal from them, so you gave them a watermelon.')
                update_table_with(mem, watermelons=get_amount(mem, 1))
                update_table_with(ctx.author, watermelons=-1)
            else:
                f'You see that {steal_from} has less watermelons than you wanted to steal from them, so you feel bad for them.'
            return

        number = random.randrange(0, 100)
        if number > 75:
            await ctx.channel.send(f'{ctx.author.mention} you stole **{num}** watermelons from {steal_from}!')
            update_table_with(mem, watermelons=-int(num / 2))
            num = get_amount(ctx.author, num)
            update_table_with(ctx.author, watermelons=num)
        else:
            await ctx.channel.send(
                f'{ctx.author.mention} you got cought stealing from {steal_from}! You paid them **{int(ceil(num / 3))}** watermelons...')
            update_table_with(ctx.author, watermelons=-int(ceil(num / 3)))
            update_table_with(mem, watermelons=get_amount(mem, int(ceil(num / 3))))


@client.command(pass_context=True)
@watermelon_channel()
async def leaderboard(ctx):
    query = "select * from users"
    cursor = conn.cursor()
    cursor.execute(query)
    records = cursor.fetchall()
    records = sorted(records, key=lambda x: (x[3], x[1] + x[2]), reverse=True)
    embed_str = ""
    place = 0
    for i, record in enumerate(records):
        try:
            watermelons_user = ctx.guild.get_member(int(record[0]))
            if watermelons_user:
                place += 1
                embed_str = embed_str.__add__(
                    f"{place}. **{get_name(watermelons_user)}** is level **{record[3]}**, with **{record[1]}** watermelons and **{record[2]}** watermelons in the bank.\n")
        except:
            await ctx.channel.send(
                f"{i}. something went wrong! is level **{record[3]}**, with **{record[1]}** watermelons and **{record[2]}** watermelons in the bank.")
    leaderboard_embed = discord.Embed(title="Our top contenders are:", description=embed_str,
                                      color=discord.Color.blue())
    await ctx.channel.send(embed=leaderboard_embed)


def listToString(lst, s):
    ret = ''
    for item in lst:
        if item != lst[0]:
            ret = ret.__add__(s)
        ret = ret.__add__(item)
    return ret


@client.command(pass_context=True)
@is_owner()
async def evalExp(ctx):
    exp = listToString(ctx.message.content.split(' ')[1:], " ")
    ret = eval(exp, {'ctx': ctx})
    await check_dm(ctx.author)
    ret = f"result for: {exp}:\n{ret}"
    await ctx.author.dm_channel.send(ret[:2000])
    print(ret)


@client.command(pass_context=True)
@watermelon_channel()
async def RPC(ctx):
    def reaction_check(reaction__, user_):
        return user_ == ctx.author and reaction__.emoji == "✅"

    async def play_again(game_msg, ctx):
        embed = game_msg.embeds[0]
        embed.description = embed.description.__add__(
            "\nReact with ✅ to play again for the same sum! Aborting in 20 seconds.")
        await game_msg.edit(embed=embed)
        await game_msg.add_reaction('✅')
        try:
            # waiting for another v reaction to start another game
            reaction_, reactor = await client.wait_for('reaction_add', check=reaction_check, timeout=20.0)
        except asyncio.TimeoutError:
            embed = discord.Embed(title="No reaction detected, aborting game.", color=discord.Color.blue())
            await game_msg.edit(embed=embed)
            await game_msg.clear_reactions()
        else:
            await game_msg.delete()
            await RPC(ctx)

    num = get_watermelon_num(ctx)

    embed = discord.Embed(title=f"Rock paper scissors game!",
                          description=f"React with ✅ to join the game! The bet is  **{num}** watermelons!\nAfter the countdown, both players will have not a lot of time (yes I take times) to send 1 (for rock), 2 (for paper), and 3 (for scissors).\n The winner will then be announced.",
                          color=discord.Color.blue())
    game_msg = await ctx.channel.send(embed=embed)
    await game_msg.add_reaction("✅")
    await game_msg.add_reaction("❎")

    def check_reaction(reaction_, user_):
        return reaction_.message.channel == ctx.channel and ((reaction_.emoji == '✅' and user_ != ctx.author) or (
                reaction_.emoji == '❎' and user_ == ctx.author)) and user_ != client.user

    # getting the other player
    player = None
    while player is None:
        try:
            reaction_, reactor = await client.wait_for('reaction_add', check=check_reaction)
        except:
            pass
        else:
            if reaction_.emoji == '✅':
                player = reactor
                if not wealth_check(player, num):
                    num = get_watermelon_user(player)[1] * 2
                    await ctx.channel.send(
                        f'{player.mention} tried to bet on more watermelons then they had, so the bet was set to the number of watermelons {player.mention} can bet on.')
            elif reaction_.emoji == '❎' and reactor == ctx.author:
                embed = discord.Embed(title="Game aborted!",
                                      description=f"By:{ctx.author.mention}",
                                      color=discord.Color.red())
                await game_msg.edit(embed=embed)
                await play_again(game_msg, ctx)
                return
    # printing the messages before the game starts (5..4..3..2..1..)
    time = 5
    while time > 0:
        embed = discord.Embed(title="Rock Paper scissors",
                              description=f"Starting in **{time}** seconds!\nAfter the countdown, both players will have not a lot of time (yes I take times) to send 1 (for rock), 2 (for paper), and 3 (for scissors).\n The winner will then be announced.",
                              color=discord.Color.random())
        await game_msg.edit(embed=embed)
        time -= 1
        await asyncio.sleep(1)

    # game should begin right here.
    def check_RPC(m: discord.message):
        return (m.author == ctx.author or m.author == player) and m.content in ["1", "2", "3"]

    embed = discord.Embed(title="Rock Paper scissors", description=f"Send it!",
                          color=discord.Color.random())
    await game_msg.edit(embed=embed)

    reactions = {f'{ctx.author.id}': None, f'{player.id}': None}
    oneAdded = False
    while reactions[f'{ctx.author.id}'] is None or reactions[f'{player.id}'] is None:
        try:
            m = await client.wait_for('message', check=check_RPC, timeout=0.7)
        except asyncio.TimeoutError:
            # something should handle bad messages
            if oneAdded:
                break
            continue
        else:
            oneAdded = True
            reactions[f'{m.author.id}'] = m.content

    # checking who won
    reaction1 = reactions[f'{ctx.author.id}']
    reaction2 = reactions[f'{player.id}']
    winner = None
    if reaction1 == reaction2:
        # draw
        pass
    # accounting for bad reactions (the big scary boolean condition is just xor)
    elif (reaction1 is None or reaction2 is None) and not reaction2 == reaction1:
        if reaction1 is None:
            winner = player
        elif reaction2 is None:
            winner = ctx.author
    elif reaction1 == '1':
        if reaction2 == '2':
            winner = player
        # we use else because it is only one of 3 cases and we already checked the other 2
        else:
            winner = ctx.author
    elif reaction1 == '2':
        if reaction2 == '3':
            winner = player
        # we use else because it is only one of 3 cases and we already checked the other 2
        else:
            winner = ctx.author
    elif reaction1 == '3':
        if reaction2 == '1':
            winner = player
        # we use else because it is only one of 3 cases and we already checked the other 2
        else:
            winner = ctx.author
    embed = discord.Embed(title="Rock Paper scissors",
                          description=f"",
                          color=discord.Color.green())

    if winner is None:
        embed.description = "No one won! It was a tie!"
    else:
        embed.description = f"{get_name(winner)} won **{int(num * 1.5)}** watermelons!"
        update_table_with(winner, watermelons=get_amount(winner, int(num * 1.5)))
        update_table_with(ctx.author if winner == player else player, watermelons=-num)

    await game_msg.edit(embed=embed)
    await play_again(game_msg, ctx)


@client.command(pass_context=True)
@watermelon_channel()
async def give(ctx):
    num = get_watermelon_num(ctx)
    user_to_give = ctx.guild.get_member_named(ctx.message.content.split(" ")[2])
    if not wealth_check(ctx.author, num):
        await ctx.channel.send(f"{ctx.author.mention}, cannot send more watermelons then you have!", delete_after=5)
        return
    update_table_with(user_to_give, watermelons=num)
    update_table_with(ctx.author, watermelons=-num)
    await ctx.channel.send(f'{ctx.author.mention}, gave **{num}** watermelons to **{get_name(user_to_give)}**!', delete_after=5)


def wealth_check(user_to_check, amount):
    if get_watermelon_user(user_to_check)[1] < amount:
        return False
    return True


def get_watermelon_num(ctx, Check_num_over_watermelons=True):
    watermelons = get_watermelon_user(ctx.author)[1 if Check_num_over_watermelons else 2]
    try:
        num = ctx.message.content.split(" ")[1]
    except:
        num = watermelons
    else:
        try:
            num = max(int(num), 0)
        except:
            pass
        if (not isinstance(num, int) and num == 'all') or num > watermelons:
            num = watermelons
    return num


@client.command(pass_context=True)
@watermelon_channel()
async def level_up(ctx):
    user = get_watermelon_user(ctx.author)
    level = user[3]
    level_up_cost = get_level_data(level)[0]
    if user[1] < level_up_cost:
        await ctx.channel.send(
            f'{ctx.author.mention}, you do not have enough watermelons to level up! You need **{level_up_cost-user}** more watermelons to level up.',
            delete_after=10)
        return
    update_table_with(ctx.author, watermelons=-level_up_cost, level=1)
    await ctx.channel.send(f"{ctx.author.mention}, you leveled up! You are now level **{level + 1}**")


# shows information about the given level.
def get_level_data(level):
    level_up_cost = 1000 * level
    watermelon_multiplier = 0.05 * level
    claim_bonus = 35 * level
    return level_up_cost, watermelon_multiplier, claim_bonus


# returns the bonuses a given user gets
def get_bonuses(user_to_get):
    # index is 3 because the 4th column is the level column
    return get_level_data(get_watermelon_user(user_to_get)[3])[1:]


# returns the amount of watermelons a user is supposed to get with all of his bonuses
def get_amount(user_to_get, amount):
    return int((1+get_bonuses(user_to_get)[0]) * amount)


@client.event
async def on_command_error(ctx: commands.Context, error: Exception):
    # I copied the next two lines straight from the source code of discord.py. I wanted it to print the errors with the line it happened in, the case, and the number of the line.
    print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
    traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
    cmnd = ctx.message.content
    cmnd = cmnd.split(' ')[0]
    if isinstance(error, commands.CommandNotFound):
        await ctx.channel.send(f'{ctx.author.mention}, command {cmnd} was not found!', delete_after=7)

    if isinstance(error, commands.MissingPermissions):
        await ctx.channel.send(f"{ctx.author.mention}, you don't have permissions to use this command!", delete_after=7)

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.channel.send(f"{ctx.author.mention}, some arguments are missing!. If you need help, use the "
                               f"!mod_mail <message> command.", delete_after=7)

    if isinstance(error, commands.CommandOnCooldown):
        await ctx.channel.send(f"{ctx.author.mention}, {error}. If you need help, use the "
                               f"!mod_mail <message> command.", delete_after=7)


watermelon_king.start()
client.run('token')
