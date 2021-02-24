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
#some things were added a lot of time ago, so they are meh.
intents = discord.Intents.default()
intents.members = True
client = commands.Bot(command_prefix='!', intents=intents)
global DEVELOPER
flag = True
# I removed all of the data
conn = psycopg2.connect(
    host="token",
    database="token",
    user="token",
    password="token")


@tasks.loop(hours=2,reconnect=True)
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
    records = sorted(records, key=lambda x: x[1] + x[2], reverse=True)
    # finding member of the server with the most watermelons
    for i, record in enumerate(records):
        watermelons_user = server.guild.get_member(int(record[0]))
        if watermelons_user is not None :
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

    if await client.fetch_guild(598157239567646721) is not None:
        await auto_activate(598157239567646721)
    if await client.fetch_guild(681165339903393998) is not None:
        await auto_activate(681165339903393998)
    # if await client.fetch_guild(757511065688080384) is not None:
    #   await auto_activate(757511065688080384)

    # if await client.fetch_guild(734095873067450398) is not None:
    #   await auto_activate(734095873067450398)
    print('Logged in as {0} ({0.id})'.format(client.user))
    print('ready!')
    print(discord.__version__)


@watermelon_king.before_loop
async def wait_for_bot():
    #wait for the bot to be ready and then some extra seconds to finish the on_ready method
    await client.wait_until_ready()
    await asyncio.sleep(10)
    print('starting')


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
            return "A".__add__(f":{self.kind.lower()}:")
        if value == 11:
            return "J".__add__(f":{self.kind.lower()}:")
        if value == 12:
            return "Q".__add__(f":{self.kind.lower()}:")
        if value == 13:
            return "K".__add__(f":{self.kind.lower()}:")
        elif 2 <= int(value) <= 10:
            return str(value).__add__(f":{self.kind.lower()}:")


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


class pokerPlayer:
    def __init__(self, player_user):
        self.user = player_user
        self.bet = 0
        self.hand = []


class pokerGame:
    def __init__(self, players, min_bet):
        self.deck = Deck(13)
        self.players = []
        for i, player in enumerate(players):
            self.players.append(pokerPlayer(player))
            self.players[-1].hand = self.deck.draw(2)
        self.bet = 0
        self.pot = min_bet * len(players)
        self.table_cards = []

    async def check_only_player_left(self, game_msg):
        if len(self.players) == 1:
            temp_embed = discord.Embed(title=f"{get_name(self.players[0].user)}' won!",
                                       description=f"They got **{self.pot}** watermelons!.",
                                       color=discord.Color.green())
            add_watermelons(self.players[0].user, self.pot)
            temp_embed.add_field(name="react with the ✅ to play again!", value="10 seconds timeout!",
                                 inline=False)
            await game_msg.edit(embed=temp_embed)

            return True
        return False

    async def actions_turn(self, game_msg, players=None, bet=0):
        self.bet = bet
        curr_player = None
        if players is None:
            players = self.players

        def turn_command_check(m):
            return m.channel == game_msg.channel and len(m.content.split(" ")) <= 2 and m.author == curr_player

        max_bet_size = get_watermelon_user(players[0].user)[1]
        for player in players:
            temp_bet_size = get_watermelon_user(player.user)[1]
            if temp_bet_size < max_bet_size:
                max_bet_size = temp_bet_size
        game_msg_embed = game_msg.embeds[0]
        stop = False
        for i, player in enumerate(players):
            curr_player = player.user
            if await self.check_only_player_left(game_msg):
                return player
            game_msg_embed.clear_fields()
            temp_embed = game_msg_embed
            temp_embed.add_field(name=f"It's {get_name(player.user)}'s turn!", value="You have 60 seconds to play!")
            await game_msg.edit(embed=temp_embed)
            msg = None
            while not stop:
                try:
                    msg = await client.wait_for('message', check=turn_command_check, timeout=60.0)
                except asyncio.TimeoutError:
                    temp_embed = game_msg_embed
                    temp_embed.clear_fields()
                    temp_embed.add_field(name=f"No command found! Folding!", value=f"oops?")
                    await game_msg.edit(embed=temp_embed)
                    self.players = [x for x in self.players if x != player]
                else:
                    stop = True
                    if msg is not None:
                        await msg.delete()
                        command = msg.content.split(" ")[0]
                        if "check" in command:
                            if player.bet == self.bet:
                                pass
                        elif "raise" in command:
                            raise_num = int(msg.content.split(" ")[1])
                            if raise_num > max_bet_size:
                                raise_num = max_bet_size
                                add_watermelons(player.user, -(raise_num + self.bet))
                                self.bet += raise_num
                                self.pot += self.bet
                                player.bet = self.bet
                                cards_str = ""
                                if self.table_cards:
                                    cards_str = "\nCards on the table:\n"
                                    for i, card in enumerate(self.table_cards):
                                        cards_str = cards_str.__add__(f"{card.to_discord_send()}, ")
                                    cards_str = cards_str[:-2]
                                temp_embed = discord.Embed(title=f"Poker game!",
                                                           description=f"(the bet amount you wanted to make was too high, so it was set as the max)\nCurrent bet: **{self.bet}**, Current pot: **{self.pot}**.{cards_str}",
                                                           color=discord.Color.green())
                            else:

                                add_watermelons(player.user, -(raise_num + self.bet))
                                self.bet += raise_num
                                self.pot += self.bet
                                player.bet = self.bet
                                cards_str = ""
                                if self.table_cards:
                                    cards_str = "\nCards on the table:\n"
                                    for i, card in enumerate(self.table_cards):
                                        cards_str = cards_str.__add__(f"{card.to_discord_send()}, ")
                                    cards_str = cards_str[:-2]
                                temp_embed = discord.Embed(title=f"Poker game!",
                                                           description=f"Current bet: **{self.bet}**, Current pot: **{self.pot}**.{cards_str}",
                                                           color=discord.Color.green())

                            await game_msg.edit(embed=temp_embed)
                            game_msg_embed = game_msg.embeds[0]

                        elif "call" in command:
                            add_watermelons(player.user, self.bet - player.bet)
                            self.pot += self.bet - player.bet
                            player.bet = self.bet
                            cards_str = ""
                            if self.table_cards:
                                cards_str = "\nCards on the table:\n"
                                for i, card in enumerate(self.table_cards):
                                    cards_str = cards_str.__add__(f"{card.to_discord_send()}, ")
                                cards_str = cards_str[:-2]

                            temp_embed = discord.Embed(title=f"Poker game!",
                                                       description=f"Current bet: **{self.bet}**, Current pot: **{self.pot}**.{cards_str}",
                                                       color=discord.Color.green())
                            await game_msg.edit(embed=temp_embed)
                        elif "fold" in command:
                            self.players = [x for x in self.players if x != player]
            stop = False
        not_fully_invested = []
        for i, player in enumerate(self.players):
            if player.bet != self.bet:
                not_fully_invested.append(player)
        if len(not_fully_invested) > 0:
            await self.actions_turn(game_msg, not_fully_invested, self.bet)
        else:
            self.bet = 0
            for i in self.players:
                i.bet = 0
            cards_str = ""
            if self.table_cards:
                cards_str = "\nCards on the table:\n"
                for i, card in enumerate(self.table_cards):
                    cards_str = cards_str.__add__(f"{card.to_discord_send()}, ")
                cards_str = cards_str[:-2]

            temp_embed = discord.Embed(title=f"Poker game!",
                                       description=f"Current bet: **{self.bet}**, Current pot: **{self.pot}**.{cards_str}",
                                       color=discord.Color.green())
            await game_msg.edit(embed=temp_embed)

    async def put_cards_on_table(self, game_msg, num):
        flop_cards = self.deck.draw(num)
        for i in flop_cards:
            self.table_cards.append(i)
        cards_str = ""
        if self.table_cards:
            cards_str = "\nCards on the table:\n"
            for i, card in enumerate(self.table_cards):
                cards_str = cards_str.__add__(f"{card.to_discord_send()}, ")
            cards_str = cards_str[:-2]
        temp_embed = discord.Embed(title=f"Poker game!",
                                   description=f"Current bet: **{self.bet}**, Current pot: **{self.pot}**.{cards_str}",
                                   color=discord.Color.green())
        await game_msg.edit(embed=temp_embed)

        return game_msg

    async def check_winner(self, game_msg):
        winner = None
        max_hand_val = 0
        evaluator = treys.Evaluator()
        board_cards = []
        for i in self.table_cards:
            board_cards.append(i.to_treys_card())
        for i, player in enumerate(self.players):
            player_hand = []
            for card in player.hand:
                player_hand.append(card.to_treys_card())
            player_hand_val = evaluator.evaluate(player_hand, board_cards)
            if player_hand_val > max_hand_val:
                max_hand_val = player_hand_val
                winner = player
        winner_hand_str = ""
        for card in winner.hand:
            winner_hand_str = winner_hand_str.__add__(f"{card.to_discord_send()}, ")
        winner_hand_str = winner_hand_str[:-2]
        winner_embed = discord.Embed(title=f"{get_name(winner.user)} won the game!",
                                     description=f"They got {self.pot} watermelons!\nTheir hand was {winner_hand_str}",
                                     color=discord.Color.gold())
        add_watermelons(winner.user, self.pot)
        winner_embed.add_field(name="react with the ✅ to play again!", value="10 seconds timeout!",
                               inline=False)

        await game_msg.edit(embed=winner_embed)


class BlackjackGame:
    def __init__(self):
        self.deck = Deck(10, True)
        self.hand = [self.deck.get_card(), self.deck.get_card()]
        self.dealer_hand = [self.deck.get_card()]

    def get_hand(self):
        return self.hand

    def get_hand_value(self):
        ret = 0
        ace_counter = 0
        for i in self.hand:
            ret += i.value
            if i.value == 1:
                ace_counter += 1
        if ret < 21:
            for i in range(ace_counter):
                if ret + 10 <= 21:
                    ret += 10
                else:
                    break

        return ret

    def get_dealer_hand(self):
        return self.dealer_hand

    def get_dealer_hand_value(self):
        ret = 0
        ace_counter = 0
        for i in self.dealer_hand:
            ret += i.value
            if i.value == 1:
                ace_counter += 1
        for i in range(ace_counter):
            if ret + 10 <= 21:
                ret += 10
            else:
                break
        return ret

    def hit(self):
        drawn_card = self.deck.get_card()
        self.hand.append(drawn_card)
        return drawn_card

    def stand(self):
        # drawing only 1 card because we already drew one for the dealer
        drawn_card = self.deck.get_card()
        self.dealer_hand.append(drawn_card)
        player_hand_value = self.get_hand_value()
        dealer_hand_value = self.get_dealer_hand_value()
        if 21 >= dealer_hand_value > 17:
            return player_hand_value >= dealer_hand_value
        else:
            while self.get_dealer_hand_value() <= 17:
                drawn_card = self.deck.get_card()
                self.dealer_hand.append(drawn_card)
            if self.get_dealer_hand_value() > 21:
                return True
            return player_hand_value >= self.get_dealer_hand_value()


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


class RaidServer:
    def __init__(self, guild_name: str):
        self.guild = get(client.guilds, name=guild_name)
        self.name = self.guild.name
        self.verify_channel = None
        self.welcome_msg = ''
        self.afk_message = ''
        self.afk_check_channel = None
        self.is_raid = True
        self.rl_role = None
        self.polls = []
        self.applicants = []
        self.key_emoji = None
        self.vcs = []
        self.locs = []

    def set_afk_check_channel(self, name: str):
        self.afk_check_channel = get(self.guild.channels, name=name)

    def set_verify_channel(self, channel_name: str):
        self.verify_channel = get(self.guild.channels, name=channel_name)

    def set_welcome_message(self, msg: str):
        self.welcome_msg = msg

    def set_rl_role(self, name: str):
        self.rl_role = get(self.guild.roles, name=name)

    def add_vc(self, name: str):
        self.vcs.append(get(self.guild.voice_channels, name=name))


class discord_server:
    def __init__(self, guild_name: str):
        self.guild = get(client.guilds, name=guild_name)
        self.reqs = Reqs(0, 0, 0, 0)
        self.name = self.guild.name
        self.verify_channel = guild_name
        self.is_raid = False
        self.welcome_msg = ''
        self.follower_role = None
        self.newcomers_log_channel = None
        self.student_role = None
        self.wannabe_role = None
        self.teacher_channel = None
        self.teacher_role = None
        self.recruiter_channel = None
        self.recruiter_role = None
        self.mod_channel = None
        self.mod_role = None
        self.member_role = None
        self.watermelon_channel = None
        self.watermelon_role = None
        self.raid_server = None
        self.polls = []
        self.applicants = []

    def set_verify_channel(self, channel_name: str):
        self.verify_channel = get(self.guild.channels, name=channel_name)

    def set_mod_channel(self, channel_name: str):
        self.mod_channel = get(self.guild.channels, name=channel_name)

    def set_welcome_message(self, msg: str):
        self.welcome_msg = msg

    def set_follower_role(self, name: str):
        self.follower_role = get(self.guild.roles, name=name)

    def set_recruiter_role(self, name: str):
        self.recruiter_role = get(self.guild.roles, name=name)

    def set_member_role(self, name: str):
        self.member_role = get(self.guild.roles, name=name)

    def set_teacher_role(self, name: str):
        self.teacher_role = get(self.guild.roles, name=name)

    def set_wannabe_role(self, name: str):
        self.wannabe_role = get(self.guild.roles, name=name)

    def set_watermelon_role(self, name: str):
        self.watermelon_role = get(self.guild.roles, name=name)

    def set_student_role(self, name: str):
        self.student_role = get(self.guild.roles, name=name)

    def set_mod_role(self, name: str):
        self.mod_role = get(self.guild.roles, name=name)

    def set_newcomers_log_channel(self, name: str):
        self.newcomers_log_channel = get(self.guild.channels, name=name)

    def set_watermelon_channel(self, name: str):
        self.watermelon_channel = get(self.guild.channels, name=name)

    def set_teacher_channel(self, name: str):
        self.teacher_channel = get(self.guild.channels, name=name)

    def set_recruiter_channel(self, name: str):
        self.recruiter_channel = get(self.guild.channels, name=name)

    def set_reqs(self, min_stat: int = 0, min_number: int = 0, min_af: int = 0, min_stars: int = 0):
        self.reqs = Reqs(min_stat, min_number, min_af, min_stars)


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


@has_permissions(manage_roles=True)
@client.command(pass_context=True)
async def set_welcome_message(ctx):
    if get_guild_named(ctx.guild.name) is None:
        await ctx.channel.send('Use !activate first')
        return
    server = get_guild_named(ctx.guild.name)
    server.set_welcome_message(ctx.message.content[21:])
    await ctx.channel.send(f'Welcome message set as {ctx.message.content[21:]}')


@has_permissions(manage_roles=True)
@client.command(pass_context=True)
async def set_follower_role(ctx):
    if get_guild_named(ctx.guild.name) is None:
        await ctx.channel.send('Use !activate first')
        return
    server = get_guild_named(ctx.guild.name)
    server.set_follower_role(ctx.message.content[19:])
    await ctx.channel.send(f'Follower role set as {ctx.message.content[19:]}')


@has_permissions(manage_roles=True)
@client.command(pass_context=True)
async def set_student_role(ctx):
    if get_guild_named(ctx.guild.name) is None:
        await ctx.channel.send('Use !activate first')
        return
    server = get_guild_named(ctx.guild.name)
    server.set_student_role(ctx.message.content[18:])
    await ctx.channel.send(f'Student role set as {ctx.message.content[18:]}')


@has_permissions(manage_roles=True)
@client.command(pass_context=True)
async def set_teacher_channel(ctx):
    if get_guild_named(ctx.guild.name) is None:
        await ctx.channel.send('Use !activate first')
        return
    server = get_guild_named(ctx.guild.name)
    server.set_teacher_channel(ctx.message.content[21:])
    await ctx.channel.send(f'Teacher channel set as {ctx.message.content[21:]}')


@has_permissions(manage_roles=True)
@client.command(pass_context=True)
async def set_teacher_role(ctx):
    if get_guild_named(ctx.guild.name) is None:
        await ctx.channel.send('Use !activate first')
        return
    server = get_guild_named(ctx.guild.name)
    server.set_teacher_role(ctx.message.content[18:])
    await ctx.channel.send(f'Teacher channel set as {ctx.message.content[18:]}')


@has_permissions(manage_roles=True)
@client.command(pass_context=True)
async def set_wannabe_role(ctx):
    if get_guild_named(ctx.guild.name) is None:
        await ctx.channel.send('Use !activate first')
        return
    server = get_guild_named(ctx.guild.name)
    server.set_wannabe_role(ctx.message.content[18:])
    await ctx.channel.send(f'Wannabe role set as {ctx.message.content[18:]}')


@has_permissions(manage_roles=True)
@client.command(pass_context=True)
async def set_verify_channel(ctx):
    if get_guild_named(ctx.guild.name) is None:
        await ctx.channel.send('Use !activate first')
        return
    server = get_guild_named(ctx.guild.name)
    server.set_verify_channel(ctx.message.content[20:])
    await ctx.channel.send(f"Verify channel set as {ctx.message.content[20:]}")


@has_permissions(manage_roles=True)
@client.command(pass_context=True)
async def set_newcomers_log_channel(ctx):
    if get_guild_named(ctx.guild.name) is None:
        await ctx.channel.send('Use !activate first')
        return
    server = get_guild_named(ctx.guild.name)
    server.set_newcomers_log_channel(ctx.message.content[27:])
    await ctx.channel.send(f"Newcomers log channel set as {ctx.message.content[27:]}")


@has_permissions(manage_roles=True)
@client.command(pass_context=True)
async def set_recruiter_channel(ctx):
    if get_guild_named(ctx.guild.name) is None:
        await ctx.channel.send('Use !activate first')
        return
    server = get_guild_named(ctx.guild.name)
    server.set_recruiter_channel(ctx.message.content[23:])
    await ctx.channel.send(f"Recruiter channel set as {ctx.message.content[23:]}")


@has_permissions(manage_roles=True)
@client.command(pass_context=True)
async def set_mod_channel(ctx):
    if get_guild_named(ctx.guild.name) is None:
        await ctx.channel.send('Use !activate first')
        return
    server = get_guild_named(ctx.guild.name)
    server.set_mod_channel(ctx.message.content[17:])
    await ctx.channel.send(f"Mod channel set as {ctx.message.content[17:]}")


@has_permissions(manage_roles=True)
@client.command(pass_context=True)
async def set_recruiter_role(ctx):
    if get_guild_named(ctx.guild.name) is None:
        await ctx.channel.send('Use !activate first')
        return
    server = get_guild_named(ctx.guild.name)
    server.set_recruiter_role(ctx.message.content[20:])
    await ctx.channel.send(f'Mod role set as {ctx.message.content[20:]}')


@has_permissions(manage_roles=True)
@client.command(pass_context=True)
async def set_mod_role(ctx):
    if get_guild_named(ctx.guild.name) is None:
        await ctx.channel.send('Use !activate first')
        return
    server = get_guild_named(ctx.guild.name)
    server.set_mod_role(ctx.message.content[14:])
    await ctx.channel.send(f'Mod role set as {ctx.message.content[14:]}')


async def auto_activate(guild_id: int = None):
    global guilds
    if guild_id == 598157239567646721:
        # hypno server
        server1 = client.get_guild(598157239567646721)
        global flag
        flag = False
        guilds = [discord_server(server1.name)]
        server = get_guild_named(server1.name)
        server.set_mod_role('Mods')
        server.set_verify_channel('verify-here')
        server.set_welcome_message(
            f"Welcome to the Vibe Gamers Server!."
            f"\n\nTo verify please follow the instructions in {server.verify_channel.mention}."
            f"\n\nIf you wish to join the in-game guild please use !apply."
            f"\n\nAny issues use !mod_mail followed by your message.")
        server.set_follower_role('Followers')
        # server.set_student_role('Students')
        # server.set_teacher_channel('instructor-chat')
        # server.set_teacher_role('Instructor')
        server.set_wannabe_role('Tadpoles')
        server.set_newcomers_log_channel('tadpole-information')
        server.set_recruiter_channel('tadpole-information')
        server.set_recruiter_role('Officer')
        server.set_mod_channel('mod-mail')
        server.set_reqs(8, 3, 10000, 65)
        server.set_member_role('Members')
        # no raid for the meanwhile because no need for this
        # server.raid_server = RaidServer(server1.name)
        # server.raid_server.set_rl_role('Trial Raid Leader')
        # server.raid_server.set_afk_check_channel('raid-afk-check')
        # server.raid_server.key_emoji = '🔑'
        # emojis = [server.raid_server.key_emoji,
        #           '<:Portal:613689700380835850>',
        #           '<:Trickster:613343143068434463>',
        #           '<:Warrior_1:613689553168891914>',
        #           '<:Paladin:613689500635234314>',
        #           '<:Knight_1:613689525801320451>',
        #           '<:Priest_1:613689574585139210>',
        #           '❌']
        # server.raid_server.emojis = EmojiList(emojis)
        # server.raid_server.afk_message = '''@here
        # If you want to join, react with <:Portal:613689700380835850> and join the specified voice channel.
        # If you are bringing any of the reactable classes, please react with the one you are planning to bring.
        # '''
        # server.raid_server.add_vc('Raiding Room')
        # server.raid_server.add_vc('Guild Chat (the therapy session)')
        # server.raid_server.add_vc('Guild Chat 2 (the cool one)')
        server.set_watermelon_channel('dank-memer')
        server.set_watermelon_role('watermelon king')
        await check_dm(DEVELOPER)
        await DEVELOPER.dm_channel.send(f'Server activated with {server1.name} special presets!')
        return
    if guild_id == 710524807317422170:
        # butterfly server, can b deleted
        server1 = client.get_guild(710524807317422170)
        guilds.append(discord_server(server1.name))
        server = get_guild_named(server1.name)
        server.set_verify_channel('welcome')
        server.welcome_msg = f"WELCOME BEAUTIFUL BUTTERFLIES. THANK YOU FOR JOINING OUR GUILD.\nTO READ FEW RULES " \
                             f"ABOUT OUR GUILD PLS CHECK {server.verify_channel.mention} CHANNEL AND TYPE !verify " \
                             f"<IGN> <TIMEZONE> to verify yourself in the server\nHOPE YOU HAVE A GOOD TIME IN OUR " \
                             f"SERVER :). "
        server.set_newcomers_log_channel('admin')
        server.set_recruiter_channel('admin')
        server.set_mod_channel('admin')
        server.set_reqs(6, 1, 0, 40)
        server.set_recruiter_role('♡¤Fountain Spirit¤♡')
        server.set_wannabe_role('Caterpillar(LTJ)')
        server.set_member_role('●Larvae●')
        server.set_follower_role('Supporters')
        await check_dm(DEVELOPER)
        await DEVELOPER.dm_channel.send(f'Server activated with {server1.name} special presets!')
    if guild_id == 681165339903393998:
        # my own server
        server1 = await client.fetch_guild(681165339903393998)
        guilds.append(discord_server(server1.name))
        server = get_guild_named(server1.name)
        server.set_watermelon_channel("general")
        server.set_verify_channel("general")


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
    return None


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
    await ctx.message.delete(delay=1)

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
    # if guild.wannabe_role not in new_member.roles:
    #   await ctx.channel.send(f"{ctx.author.mention}, {give_to} isn't a {guild.wannabe_role} yet!")
    #   return
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
        msg = await ctx.author.send(f"{ctx.author.mention}, command {apply} can't be used here!")
        await msg.delete(delay=5)
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
        msg = await writer.dm_channel.send(
            f'{writer.mention} something went wrong... please use the !mod_mail <message> and tell us what happened!')
        await msg.delete()
        return

    if ctx.channel != server.verify_channel:
        msg = await writer.dm_channel.send(f'Please use the {server.verify_channel.mention} channel!')
        await msg.delete()

        return

    if rolee not in writer.roles:
        msg = await writer.dm_channel.send(
            f'{writer.mention} please use the !verify <ign> <timezone> command first')
        await msg.delete()
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
        msg = await ctx.channel.send(f'{ctx.author.mention}, please type the question for the poll you just created('
                                     f'you have a minute to do so)')
        await msg.delete(delay=5)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await client.wait_for('message', check=check, timeout=60.0)
        except asyncio.TimeoutError:
            msg_to_delete = await ctx.channel.send(
                f'{ctx.author.mention}, no question was sent so poll creation was aborted.')
            await msg_to_delete.delete(delay=5.0)
        else:
            created_poll.set_question(msg.content)
            msg_to_delete = await ctx.channel.send(
                f'{ctx.author.mention}, poll created! use **!poll send <channel name>** to send it!')
            await msg_to_delete.delete(delay=5.0)
        finally:
            await msg.delete(delay=3.0)

    if command == "send":
        embed1 = None
        for i in server.polls:
            if i.poll_author == ctx.author:
                embed1 = discord.Embed(title=i.question, description="", color=discord.Color.blue())
                server.polls.remove(i)
                break
        if not embed1:
            msg = await ctx.channel.send(f"{ctx.author.mention}, please use **!poll create** first!")
            await msg.delete(delay=5)
            return
        msg = await send_to_channel.send(embed=embed1)

        await msg.add_reaction("✅")
        await msg.add_reaction("❎")


@has_permissions(manage_nicknames=True)
@client.command(pass_context=True)
async def DM(ctx, nickname: str = None, *, msg):
    await ctx.message.delete()
    if not nickname:
        msg = await ctx.channel.send(f'{ctx.author.mention}, who do you want to send it to?')
        await msg.delete(delay=3)
    mem = ctx.guild.get_member_named(nickname)
    if not mem:
        msg = await ctx.channel.send(f'{ctx.author.mention}, {nickname} was not found!')
        await msg.delete(delay=3)
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


@client.command(pass_context=True)
async def afk(ctx, vc_number: int, loc, *, dungeon_name: str):
    server = get_guild_named(ctx.guild.name)
    msg = None
    if not server.is_raid:
        if server.raid_server:
            server = server.raid_server
        else:
            msg = await ctx.channel.send(f"{ctx.author.mention}, this server is not set as a raid server!")
            await msg.delete(delay=5)
            return
    send_to = server.afk_check_channel
    if ctx.author.roles[-1] < server.rl_role:
        msg = await ctx.channel.send(f"{ctx.author.mention}, you are not a raid leader!")
    elif not send_to:
        msg = await ctx.channel.send(f"{ctx.author.mention}, no afk check channel found!")
    elif loc in server.locs:
        msg = await ctx.channel.send(f"{ctx.author.mention}, the location is already being used!")
    if msg:
        await msg.delete(delay=5)
        return
    name = ctx.author.name
    if ctx.author.nick:
        name = ctx.author.nick
    text = server.afk_message
    vc = server.vcs[vc_number - 1]
    embed1 = discord.Embed(title=f"New {dungeon_name}!", description=f'Join {vc.mention} to join the raid!')
    embed1.add_field(name=f"{name}'s {dungeon_name}", value=text, inline=False)
    msg = await send_to.send(embed=embed1)
    for i in server.emojis.emojis:
        await msg.add_reaction(i)
    server.locs.append([loc, embed1.description])

    def check_rl(reaction_, user_):
        return str(reaction_.emoji) == '❌' and user_ == ctx.author

    reaction_rl, rl = await client.wait_for('reaction_add', timeout=60.0, check=check_rl)
    if reaction_rl and rl:
        embed1 = discord.Embed(title="Afk over, please wait for the next one!")
        await reaction_rl.message.edit(embed=embed1)
        return


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
async def blackjack(ctx, num=0):
    reward = 0
    # I don't even like watermelons. Should have gone with strawberries.
    try:
        await ctx.message.delete()
    except:
        pass

    server = get_guild_named(ctx.guild.name)
    if ctx.channel != server.watermelon_channel:
        msg = await ctx.channel.send(
            f'{ctx.author.mention}, please use the {server.watermelon_channel.mention} channel!')
        await msg.delete(delay=5)
        return
    watermelons = get_watermelon_user(ctx.author)[1]
    if watermelons < num:
        msg=await ctx.channel.send(
            f"{ctx.author.mention}, you can't play on more watermelons then you have! starting the game with a 0 gamble.")
        await msg.delete(delay=5)
        num = 0
    # up until here everything was just making sure everything is ok(the right channel) and getting the server.
    game = BlackjackGame()
    user_hand = game.get_hand()
    stop = False

    def get_hand_str(hand):
        ret = ""
        for card_in_hand in hand:
            ret = ret.__add__(
                f"**{card_in_hand.value if card_in_hand.value != 1 else 'A'}**:{card_in_hand.kind.lower()}: ")
        ret = ret[:-1]
        return ret

    # creating the first Embed!
    game_info = get_hand_str(user_hand).__add__(f"\nTotal:**{game.get_hand_value()}**")
    dealer_hand_info = get_hand_str(game.get_dealer_hand()).__add__(f"\nTotal:**{game.get_dealer_hand_value()}**")

    name = get_name(ctx.author)
    embed = discord.Embed(title=f"{name}'s Blackjack game", color=discord.Color.blue(),
                          description="react with ✅ to hit, and with ❎ to stand. If you "
                                      "want an ace to count as a 1 and not as 11, just hit and the game will "
                                      "continue.")
    embed.add_field(name=f"{name}'s hand", value=game_info)
    embed.add_field(name=f"Dealer's first card", value=dealer_hand_info)

    # checking if we got a true blackjack (21 is the sum with 2 cards drawn)

    if game.get_hand_value() == 21:
        # if yes, change the Embed to the victory message
        embed = discord.Embed(title=f"{name}'s Blackjack game", color=discord.Color.green())
        embed.add_field(name=f"{name}'s hand", value=game_info)
        embed.add_field(name=f"Dealer's first card", value=dealer_hand_info)
        embed.add_field(name="You won!", value="Winner winner chicken dinner! True Blackjack!", inline=False)
        embed.add_field(name="react with the ✅ to play again!", value="10 seconds timeout!",
                        inline=False)
        reward = 2*num
        stop = True

    game_msg = await ctx.channel.send(embed=embed)
    await game_msg.add_reaction("✅")
    await game_msg.add_reaction("❎")

    def reaction_check(reaction__, user_):
        return user_ == ctx.author and (reaction__.emoji == "✅" or reaction__.emoji == "❎")

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
            if reaction_.emoji == "✅":
                game.hit()
                user_hand = game.get_hand()
                hand_value = game.get_hand_value()
                game_info = get_hand_str(user_hand).__add__(f"\nTotal:**{hand_value}**")
                if hand_value < 22:
                    embed = discord.Embed(title=f"{name}'s Blackjack game", color=discord.Color.blue())
                    embed.add_field(name=f"{name}'s hand", value=game_info)
                    embed.add_field(name=f"Dealer's first card", value=dealer_hand_info)

                if hand_value == 21:
                    embed = discord.Embed(title=f"{name}'s Blackjack game", color=discord.Color.green())
                    embed.add_field(name=f"{name}'s hand", value=game_info)
                    embed.add_field(name=f"Dealer's first card", value=dealer_hand_info)
                    embed.add_field(name="You won!", value="Winner winner chicken dinner! Blackjack!", inline=False)
                    embed.add_field(name="react with the ✅ to play again!", value="10 seconds timeout!",
                                    inline=False)
                    reward = num

                    stop = True
                if hand_value > 21:
                    embed = discord.Embed(title=f"{name}'s Blackjack game", color=discord.Color.red())
                    embed.add_field(name=f"{name}'s hand", value=game_info)
                    embed.add_field(name=f"Dealer's first card", value=dealer_hand_info)
                    embed.add_field(name=f"You lost!",
                                    value=f"(Your hand was more then 21, it was {hand_value})", inline=False)
                    embed.add_field(name="react with the ✅ to play again!", value="10 seconds timeout!",
                                    inline=False)
                    reward = -num
                    stop = True
            elif reaction_.emoji == "❎":
                # stand: check who won
                stop = True
                win = game.stand()
                reward = num if win else -num
                # print(win)
                hand_value = game.get_hand_value()
                dealer_hand_info = get_hand_str(game.get_dealer_hand()).__add__(
                    f"\nTotal:**{game.get_dealer_hand_value()}**")
                # print(dealer_hand_info)
                user_hand = game.get_hand()
                game_info = get_hand_str(user_hand).__add__(f"\nTotal:**{hand_value}**")
                embed = discord.Embed(title=f"{name}'s Blackjack game",
                                      color=discord.Color.green() if win else discord.Color.red())
                embed.add_field(name=f"{name}'s hand", value=game_info)
                embed.add_field(name=f"Dealer's hand", value=dealer_hand_info)
                embed.add_field(name="You won!" if win else "You lost!",
                                value="Winner winner chicken dinner!" if win else "Better luck next time!",
                                inline=False)
                embed.add_field(name="react with the ✅ to play again!", value="10 seconds timeout!",
                                inline=False)
            await game_msg.edit(embed=embed)
    try:
        #giving the reward to the user
        add_watermelons(ctx.author,reward)
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
            await blackjack(ctx, num)


def create_watermelon_user(user_to_create: discord.member):
    id = str(user_to_create.id)
    watermelons = 100
    bank_watermelons = 0
    cursor = conn.cursor()
    try:

        postgres_query = " INSERT INTO users (id,watermelons,bank) VALUES (%s,%s,%s)"
        record_to_insert = (id, watermelons, bank_watermelons)
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


def add_watermelons(user_to_add: discord.client, number):
    id = str(user_to_add.id)
    cursor = conn.cursor()
    try:
        watermelons = get_watermelon_user(user_to_add)[1]
        if watermelons + number < 0 and number < 0:
            return -1

        postgres_query = "update users set watermelons = %s where id = %s"
        parms = (watermelons + number, id)
        cursor.execute(postgres_query, parms)
        conn.commit()

        cursor.close()

        return watermelons + number
    except (Exception, psycopg2.Error) as error:
        print("Error in update operation", error)


def add_bank(user_to_add: discord.client, number):
    id = str(user_to_add.id)
    cursor = conn.cursor()
    try:
        bank = get_watermelon_user(user_to_add)[2]
        if bank + number < 0 and number < 0:
            return -1
        postgres_query = "update users set bank = %s where id = %s"
        parms = (bank + number, id)
        cursor.execute(postgres_query, parms)
        conn.commit()

        cursor.close()

        return bank + number
    except (Exception, psycopg2.Error) as error:
        print("Error in update operation", error)


@commands.cooldown(1, 90, commands.BucketType.user)
@client.command(pass_context=True)
async def claim(ctx):
    server = get_guild_named(ctx.guild.name)
    if ctx.channel != server.watermelon_channel:
        msg = await ctx.channel.send(
            f'{ctx.author.mention}, please use the {server.watermelon_channel.mention} channel!')
        await msg.delete(delay=5)
        return
    add_watermelons(ctx.author, 35)
    await ctx.channel.send(f'{ctx.author.mention}, you got 35 watermelons!')


@client.command(pass_context=True)
async def bank(ctx, num: int):
    server = get_guild_named(ctx.guild.name)
    watermelons = get_watermelon_user(ctx.author)[1]
    if ctx.channel != server.watermelon_channel:
        msg = await ctx.channel.send(
            f'{ctx.author.mention}, please use the {server.watermelon_channel.mention} channel!')
        await msg.delete(delay=5)
        return
    if num < 0:
        msg = await ctx.channel.send(f'{ctx.author.mention}, cannot bank negative values!')
        await msg.delete(delay=5)
        return
    if watermelons - num < 0:
        msg = await ctx.channel.send(f"{ctx.author.mention}, you can't bank more watermelons then you have!")
        await msg.delete(delay=5)
        return

    add_bank(ctx.author, num)
    add_watermelons(ctx.author, -num)
    await ctx.channel.send(f"{ctx.author.mention}, You banked {num} watermelons!")


@client.command(pass_context=True)
async def withdraw(ctx, num: int):
    server = get_guild_named(ctx.guild.name)
    bank_watermelons = get_watermelon_user(ctx.author)[2]
    if ctx.channel != server.watermelon_channel:
        msg = await ctx.channel.send(
            f'{ctx.author.mention}, please use the {server.watermelon_channel.mention} channel!')
        await msg.delete(delay=5)
        return
    if num < 0:
        msg = await ctx.channel.send(f'{ctx.author.mention}, cannot withdraw negative values!')
        await msg.delete(delay=5)
        return
    if num > bank_watermelons:
        msg = await ctx.channel.send(
            f"{ctx.author.mention}, you can't withdraw more watermelons then you have in the bank!")
        await msg.delete(delay=5)
        return

    add_bank(ctx.author, -num)
    add_watermelons(ctx.author, num)
    await ctx.channel.send(f"{ctx.author.mention}, You withdrew {num} watermelons!")


@client.command(pass_context=True)
async def show(ctx):
    server = get_guild_named(ctx.guild.name)
    if ctx.channel != server.watermelon_channel:
        msg = await ctx.channel.send(
            f'{ctx.author.mention}, please use the {server.watermelon_channel.mention} channel!')
        await msg.delete(delay=5)
        return
    try:
        watermelons, bank_watermelons = get_watermelon_user(ctx.author)[1:]
        await ctx.channel.send(
            f"{ctx.author.mention}, you have {watermelons} watermelons, and {bank_watermelons} watermelons in the bank!")
    except:
        await ctx.channel.send(f"{ctx.author.mention}, oops! Something went wrong!")


@client.command(pass_context=True)
async def peak(ctx, user_name):
    server = get_guild_named(ctx.guild.name)
    if ctx.channel != server.watermelon_channel:
        msg = await ctx.channel.send(
            f'{ctx.author.mention}, please use the {server.watermelon_channel.mention} channel!')
        await msg.delete(delay=5)
        return

    try:
        mem = ctx.guild.get_member_named(user_name)
        watermelons, bank_watermelons = get_watermelon_user(mem)[1:]
        await ctx.channel.send(
            f"{ctx.author.mention}, {user_name} has {watermelons} watermelons, and {bank_watermelons} watermelons in the bank!")
    except:
        await ctx.channel.send(f"{ctx.author.mention}, oops! Something went wrong!")


@client.command(pass_context=True)
async def gamble(ctx, num: int = 0):
    server = get_guild_named(ctx.guild.name)
    if ctx.channel != server.watermelon_channel:
        msg = await ctx.channel.send(
            f'{ctx.author.mention}, please use the {server.watermelon_channel.mention} channel!')
        await msg.delete(delay=5)
        return
    watermelons = get_watermelon_user(ctx.author)[1]
    if watermelons < num:
        await ctx.channel.send(
            f"{ctx.author.mention}, you can't gamble on more then you have!")
        return

    if num < 0:
        await ctx.channel.send(f'{ctx.author.mention}, cannot gamble negative values!')
        return
    else:
        number = random.randrange(0, 100)
        if number >= 33:
            await ctx.channel.send(f'{ctx.author.mention} you won {num} watermelons!')
            add_watermelons(ctx.author, num)
        else:
            await ctx.channel.send(f'{ctx.author.mention} you lost {num} watermelons...')
            add_watermelons(ctx.author, -num)



@client.command(pass_context=True)
async def steal(ctx):
    num = int(ctx.message.content.split(" ")[1])
    steal_from = listToString(ctx.message.content.split(" ")[2:]," ")
    server = get_guild_named(ctx.guild.name)
    if ctx.channel != server.watermelon_channel:
        msg = await ctx.channel.send(
            f'{ctx.author.mention}, please use the {server.watermelon_channel.mention} channel!')
        await msg.delete(delay=5)
        return
    watermelons = get_watermelon_user(ctx.author)[1]
    if steal_from == get_name(ctx.author):
        if watermelons > 2:
            await ctx.channel.send(
                "Imagine trying to steal from yourself! LOL. You were fined a watermelon for stupidity")
            add_watermelons(ctx.author, -1)
        else:
            ctx.channel.send("Imagine trying to steal from yourself! LOL.")
        return
    if num is None:
        await ctx.channel.send('Please specify the amount!')
        return

    if num < 0:
        await ctx.channel.send(f'{ctx.author.mention}, cannot steal negative values!')
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
                add_watermelons(mem, 1)
                add_watermelons(ctx.author, -1)
            else:
                f'You see that {steal_from} has less watermelons than you wanted to steal from them, so you feel bad for them.'
            return

        number = random.randrange(0, 10)
        if number % 4 == 0:
            await ctx.channel.send(f'{ctx.author.mention} you stole {num} watermelons from {steal_from}!')
            add_watermelons(ctx.author, num)
            add_watermelons(mem, -num)
        else:
            await ctx.channel.send(
                f'{ctx.author.mention} you got cought stealing from {steal_from}! You paid them {int(ceil(num / 3))} watermelons...')
            add_watermelons(ctx.author, -int(ceil(num / 3)))
            add_watermelons(mem, int(ceil(num / 3)))


@client.command(pass_context=True)
async def leaderboard(ctx):
    server = get_guild_named(ctx.guild.name)
    if ctx.channel != server.watermelon_channel:
        msg = await ctx.channel.send(
            f'{ctx.author.mention}, please use the {server.watermelon_channel.mention} channel!')
        await msg.delete(delay=5)
        return
    query = "select * from users"
    cursor = conn.cursor()
    cursor.execute(query)
    records = cursor.fetchall()
    records = sorted(records, key=lambda x: x[1] + x[2], reverse=True)
    embed_str = ""
    place = 0
    for i, record in enumerate(records):
        try:
            watermelons_user = ctx.guild.get_member(int(record[0]))
            if watermelons_user:
                place += 1
                embed_str = embed_str.__add__(
                    f"{place}. **{get_name(watermelons_user)}**, with **{record[1]}** watermelons and **{record[2]}** watermelons in the bank.\n")
        except:
            await ctx.channel.send(
                f"{i}. something went wrong!, with {record[1]} watermelons and {record[2]} watermelons in the bank.")
    leaderboard_embed = discord.Embed(title="Our top contenders are:", description=embed_str,
                                      color=discord.Color.blue())
    await ctx.channel.send(embed=leaderboard_embed)


@client.command(pass_context=True)
async def poker(ctx, min_bet):
    min_bet = int(min_bet)
    embed = discord.Embed(title=f"Poker game!",
                          description=f"React with ✅ to join the game! The minimum bet is  {min_bet} watermelons!",
                          color=discord.Color.blue())
    game_msg = await ctx.channel.send(embed=embed)
    await game_msg.add_reaction("✅")
    await game_msg.add_reaction("❎")

    def check_reaction(reaction_, user_):
        return reaction_.message.channel == ctx.channel and (
                reaction_.emoji == '✅' or reaction_.emoji == '❎') and user_ != client.user

    players = []
    while True:
        try:
            reaction_, reactor = await client.wait_for('reaction_add', check=check_reaction)
        except:
            pass
        else:
            if reaction_.emoji == '✅':
                players.append(reactor)
            elif reaction_.emoji == '❎' and reactor == ctx.author:
                break
    for player in players:
        if get_watermelon_user(player)[1] < min_bet:
            players = [x for x in players if x != player]
    game = pokerGame(players, min_bet)
    players_str = ""
    for player in players:
        players_str = players_str.__add__(f"{get_name(player)}, ")
        add_watermelons(player, -min_bet)
    await game_msg.edit(embed=discord.Embed(title="game ready!", description=f"players:\n{players_str[:-2]}",
                                            color=discord.Color.green()))
    await game_msg.clear_reactions()
    for player in game.players:
        await check_dm(player.user)
        cards_str = ""
        for card in player.hand:
            cards_str = cards_str.__add__(f"{card.to_discord_send()}, ")
        await player.user.dm_channel.send(f"Hey {get_name(player.user)}!\nYour cards are: {cards_str[:-2]}")
    embed = discord.Embed(title=f"Poker game!",
                          description=f"Current bet: **{game.bet}**, Current pot: **{game.pot}**",
                          color=discord.Color.green())
    await game_msg.add_reaction("✅")
    game_ended = False
    await game_msg.edit(embed=embed)
    if await game.actions_turn(game_msg):
        game_ended = True
    if not game_ended:
        game_msg = await game.put_cards_on_table(game_msg, 3)
        if await game.actions_turn(game_msg):
            game_ended = True
    if not game_ended:
        game_msg = await game.put_cards_on_table(game_msg, 1)
        if await game.actions_turn(game_msg):
            game_ended = True
    if not game_ended:
        game_msg = await game.put_cards_on_table(game_msg, 1)
        if await game.actions_turn(game_msg):
            game_ended = True
    if not game_ended:
        await game.check_winner(game_msg)

    try:
        reaction_, reactor = await client.wait_for('reaction_add', check=check_reaction, timeout=10.0)
    except asyncio.TimeoutError:
        embed = discord.Embed(title="No reaction detected, aborting game.", color=discord.Color.blue())
        await game_msg.edit(embed=embed)
        await game_msg.clear_reactions()

    else:
        if reaction_.emoji == "✅":
            await game_msg.delete()
            await poker(ctx, min_bet)


@client.command(pass_context=True)
async def among_us(ctx):
    if ctx.guild.name != "הגזענים":
        return
    await ctx.message.delete()
    category = get(ctx.guild.categories, id=757511066136870952)
    game_channel = await ctx.guild.create_voice_channel(name=f"New Among us game!", user_limit=10, category=category,
                                                        position=0)
    invite = await game_channel.create_invite()
    game_msg = await ctx.channel.send(invite)
    await game_msg.add_reaction('✅')

    def check_reaction(reaction_, user_):
        return reaction_.emoji == "✅" and user_ == ctx.author

    stop = False
    while not stop:
        try:
            reaction_, reactor = await client.wait_for('reaction_add', check=check_reaction)
        except asyncio.TimeoutError:
            pass
        else:
            stop = True
            await game_msg.delete()
            await game_channel.delete()


#@client.event
async def on_command_error(ctx: commands.Context, error: Exception):
    print(error)
    print(error.__cause__)
    print(error.__context__)
    msg = None
    cmnd = ctx.message.content
    cmnd = cmnd.split(' ')[0]
    if isinstance(error, commands.CommandNotFound):
        msg = await ctx.channel.send(f'{ctx.author.mention}, command {cmnd} was not found!')

    if isinstance(error, commands.MissingPermissions):
        msg = await ctx.channel.send(f"{ctx.author.mention}, you don't have permissions to use this command!")

    if isinstance(error, commands.MissingRequiredArgument):
        msg = await ctx.channel.send(f"{ctx.author.mention}, some arguments are missing!. If you need help, use the "
                                     f"!mod_mail <message> command.")

    if isinstance(error, commands.CommandOnCooldown):
        msg = await ctx.channel.send(f"{ctx.author.mention}, {error}. If you need help, use the "
                                     f"!mod_mail <message> command.")

    if error and msg:
        await msg.delete(delay=7)


def listToString(lst, s):
    ret = ''
    for item in lst:
        if item != lst[0]:
            ret = ret.__add__(s)
        ret = ret.__add__(item)
    return ret


def is_owner():
    def predicate(ctx):
        return ctx.author == DEVELOPER

    return commands.check(predicate)


@client.command(pass_context=True)
@is_owner()
async def evalExp(ctx):
    exp = listToString(ctx.message.content.split(' ')[1:], " ")
    ret = eval(exp, {'ctx': ctx})
    await check_dm(ctx.author)
    ret = f"result for: {exp}:\n{ret}"
    await ctx.author.dm_channel.send(ret[:2000])
    print(ret)


watermelon_king.start()
#discord token removed.
client.run('Yep token again')
