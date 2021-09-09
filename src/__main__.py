#!/usr/bin/env python3

from typing import Union, Dict
from pathlib import Path
import datetime
import discord
import dotenv
import time
import json
import os

# Next version needs to implement thread safety

def _read_json(path: str) -> dict:
	with open(path, "r") as json_file:
		return json.load(json_file)

def _write_json(path: str, data: dict, neat: bool = False):
	with open(path, "w") as json_file:
		if neat:
			json.dump(data, json_file, indent = 4)
		else:
			json.dump(data, json_file)

_project_root = Path(os.path.abspath(__file__)).parent.parent.__str__()
_months = (
	"jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
	"january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
	"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"
)

class EqualBot(discord.Client):

	def __init__(self):
		super().__init__(intents = discord.Intents(messages = True, members = True, guilds = True))

		self.chaos_file_path = os.path.join(_project_root, "data", "chaos.json")

		bot_config = _read_json(os.path.join(_project_root, "config", "bot.json"))

		self.historical_search_threshold = bot_config.get("Historical Search Threshold (in seconds)", 30)
		self.leaderboard_channel_id = bot_config.get("Leaderboard Channel ID", None)
		self.equal_channel_id = bot_config.get("Equal Channel ID", None)
		self.equal_role_id = bot_config.get("Equal Role ID", None)
		self.chaos_channel_id = bot_config.get("Chaos Channel ID", None)
		self.historical_purge = bot_config.get("Historical Purge", False)

		self.posts_to_confirm: Dict[int, str] = {}

		birthday_data = _read_json(os.path.join(_project_root, "data", "birthdays.json"))

		self.birthday_cache = [ # 2d matrix making a calendar
			[0] * 31, [0] * 29, [0] * 31, [0] * 30,
			[0] * 31, [0] * 30, [0] * 31, [0] * 31,
			[0] * 30, [0] * 31, [0] * 30, [0] * 31
		]

		for birthday in birthday_data.values():
			if not isinstance(birthday, dict):
				raise ValueError("Invalid birthday entry, must be a dictionary")

			try:
				month = int(birthday.get("month", 13))
			except ValueError:
				raise ValueError(f"Invalid month, must be a number, not \"{birthday.get('month')}\"")

			try:
				day = int(birthday.get("day", 32))
			except ValueError:
				raise ValueError(f"Invalid day, must be a number, not \"{birthday.get('day')}\"")

			if month < 1 or month > 12:
				raise ValueError(f"Invalid month \"{month}\", must be 1 <= month <= 12")

			if day < 1 or day > self.birthday_cache[month - 1].__len__():
				raise ValueError(f"Invalid day \"{day}\", must be 1 <= day <= {self.birthday_cache[month - 1].__len__()}")

			self.birthday_cache[month - 1][day - 1] += 1

	async def increase_chaos(self, user_id: Union[int, str], user_name: str):
		user_id = str(user_id)
		chaos_data = _read_json(self.chaos_file_path)

		if user_id not in chaos_data:
			chaos_data[user_id] = {"name": user_name, "points": 0, "chaos_posts": []}

		chaos_data[user_id]["points"] += 1
		_write_json(self.chaos_file_path, chaos_data)
		await self.update_leaderboard()

	async def decrease_chaos(self, user_id: Union[int, str], user_name: str):
		user_id = str(user_id)
		chaos_data = _read_json(self.chaos_file_path)

		if user_id not in chaos_data:
			chaos_data[user_id] = {"name": user_name, "points": 0, "chaos_posts": []}

		chaos_data[user_id]["points"] -= 1

		if chaos_data[user_id]["points"] < 0: # Prevent negative
			chaos_data[user_id]["points"] = 0

		_write_json(self.chaos_file_path, chaos_data)
		await self.update_leaderboard()

	async def generate_leaderboard_messaage(self) -> str:
		chaos_data = _read_json(self.chaos_file_path)

		longest_username_length = max(chaos_data.values(), key = lambda x: x["name"].__len__())["name"].__len__()
		longest_chaos_points = max(chaos_data.values(), key = lambda x: (x["points"] - x["chaos_posts"].__len__() * 50).__str__().__len__())
		longest_chaos_points = (longest_chaos_points["points"] - longest_chaos_points["chaos_posts"].__len__() * 50).__str__().__len__()
		longest_chaos_posts = max(chaos_data.values(), key = lambda x: x["chaos_posts"].__len__().__str__().__len__())["chaos_posts"].__len__().__str__().__len__()

		output = ""

		for user_data in sorted(chaos_data.values(), key = lambda x: x["points"], reverse = True):
			output += f"\n[ {user_data['name']:<{longest_username_length}} ][ {(user_data['points'] - user_data['chaos_posts'].__len__() * 50):^{longest_chaos_points}} ][ {user_data['chaos_posts'].__len__():>{longest_chaos_posts}} ]"

		return f"```md{output}\n```"

	async def update_leaderboard(self):
		leaderboard: discord.TextChannel = self.get_channel(self.leaderboard_channel_id)

		if leaderboard is None:
			print(f"Unable to update leaderboard, couldn't find channel with id \"{self.leaderboard_channel_id}\"")
			return

		async for message in leaderboard.history(oldest_first = True, limit = None):
			if message.author.id == self.user.id:
				await message.edit(content = await self.generate_leaderboard_messaage())
				return

		await leaderboard.send(content = await self.generate_leaderboard_messaage())

	def update_last_online(self):
		_write_json(os.path.join(_project_root, "data", "last_online.json"), int(time.time()))

	async def on_ready(self):
		print(f"Readying as {self.user} ({self.user.id})")

		print(f"Use this link to join your bot to your server: https://discord.com/api/oauth2/authorize?client_id={self.user.id}&permissions=8&scope=bot")

		await self.change_presence(activity = discord.Game("God"))

		last_online_path = os.path.join(_project_root, "data", "last_online.json")

		should_run_historical_search = False

		if os.path.isfile(last_online_path):
			last_online = _read_json(last_online_path)

			delta = int((datetime.datetime.now() - datetime.datetime.fromtimestamp(last_online)).total_seconds())

			if delta >= self.historical_search_threshold:
				print("\tLast online ", delta, " second", "" if delta == 1 else "s", " ago which is greater than or equal to ", self.historical_search_threshold, " second", "" if self.historical_search_threshold == 1 else "s", sep="")
				should_run_historical_search = True
		else:
			should_run_historical_search = True

		self.update_last_online()

		if should_run_historical_search or not os.path.isfile(self.chaos_file_path): # Trigger chaos points historical search
			print("\tRunning historical search to calculate chaos points")
			chaos_data = {}

			equal_channel: discord.TextChannel = self.get_channel(self.equal_channel_id)

			if equal_channel is not None:
				message: discord.Message
				async for message in equal_channel.history(limit = None):
					author_id = str(message.author.id)
					if author_id not in chaos_data:
						chaos_data[author_id] = {"name": message.author.name, "points": 0, "chaos_posts": []}

					check = await self.check_message(message)
					if check == 1:
						chaos_data[author_id]["points"] += 1

					elif check == -1:
						if self.historical_purge:
							print("\t\tPurging message by ", message.author.name, " (", message.author.id, ") saying ", message.clean_content, sep = "")
							await message.delete()
						else:
							print("\t\tNot purging bad message at", message.jump_url)

						chaos_data[author_id]["points"] -= 1

				print("\tSaving new chaos data")
				_write_json(self.chaos_file_path, chaos_data)

		await self.update_leaderboard()

		print("Readied")

	async def check_message(self, message: discord.Message) -> int:
		if message.author.id == self.user.id: # Don't listen to myself by mistake
			return 0

		if message.channel is not None:
			if message.channel.id != self.equal_channel_id: # Equal text channel
				return 0

			if message.reference is not None and not message.is_system(): # Prevent replies
				return -1

			if message.attachments.__len__(): # Don't allow attachments
				return -1

			if message.reactions.__len__(): # Don't allow reactions
				await message.clear_reactions() # Auto fix

			content = message.clean_content

			if content == "Equal":
				return 1

			day = message.created_at

			if content == "Equal 🎄" and day.month == 12 and day.day == 25: # Allow Christmas emote
				return 1

			if content == "Equal 🎂": # Allow birthdays
				if self.birthday_cache[day.month - 1][day.day - 1]: # 2d matrix of birthdays, zero-based
					return 1

			return -1

	def get_balance(self, user_id: int) -> int:
		user_id = str(user_id)
		chaos_data = _read_json(self.chaos_file_path)

		if user_id not in chaos_data:
			return 0

		return chaos_data[user_id]["points"] - chaos_data[user_id]["chaos_posts"].__len__() * 50

	async def message_handle(self, message: discord.Message, edited: bool = False):
		if message.guild is None and not edited: # Unmanaged, DMs
			contents = message.clean_content.lower().replace("\n", " ").split(" ")

			cmd, args = contents[0], contents[1:]
			del contents

			if cmd == "bday": # Should I check if someone changes their bday a bunch to be able to post 🎂's? No, rate limiting for something like this? No
				if args.__len__() == 2:
					month, day = args
					del args

					try:
						month = _months.index(month) % 12
					except ValueError:
						await message.reply(embed = discord.Embed(title = "bday Command", description = "Invalid month", color = discord.Color.red())\
							.add_field(name = "month", value = f"The month can be a three letter abbreviation (Jan, Feb, Nov, or Dec), full names (April, August, September, or July), or a number (3, 5, 6, or 10)\n\nNot \"{month}\""), mention_author=False)
					else:
						try:
							day = int(day) # Could check length before too as a number over 2 digits isn't allowed
						except ValueError:
							await message.reply(embed = discord.Embed(title = "bday Command", description = "Invalid day", color = discord.Color.red())\
								.add_field(name = "day", value = f"The day must be a number\n\nNot \"{day}\""), mention_author=False)

						
						if day < 1 or day > self.birthday_cache[month].__len__():
							await message.reply(embed = discord.Embed(title = "bday Command", description = "Invalid day", color = discord.Color.red())\
								.add_field(name = "day", value = f"The day must be between 1 and {self.birthday_cache[month].__len__()}, {day} isn't"), mention_author=False)
						else:
							user_id = str(message.author.id)
							birthday_data = _read_json(os.path.join(_project_root, "data", "birthdays.json"))

							if user_id in birthday_data:
								old_birthday = birthday_data[user_id].copy()

								if old_birthday.get("month") == month + 1 and old_birthday.get("day") == day: # Same day
									await message.reply(embed = discord.Embed(title = "bday Command", description = f"{_months[month + 12].title()} {day} is already your birthday!", color = discord.Color.red()), mention_author=False)
									self.update_last_online()
									return

							self.birthday_cache[month][day - 1] += 1 # Modify loaded cache
							birthday_data[user_id] = {"month": month + 1, "day": day}
							_write_json(os.path.join(_project_root, "data", "birthdays.json"), birthday_data)

							if user_id in birthday_data:
								self.birthday_cache[old_birthday.get("month") - 1][old_birthday.get("day") - 1] -= 1 # Modify loaded cache

								await message.reply(embed = discord.Embed(title = "bday Command", description = "Birthday set!", color = discord.Color.green())\
									.add_field(name = "Updated from", value = f"{_months[old_birthday.get('month') + 11].title()} {old_birthday.get('day')}")\
									.add_field(name = "To", value = f"{_months[month + 12].title()} {day}"), mention_author=False)

							else:
								await message.reply(embed = discord.Embed(title = "bday Command", description = "Birthday set!", color = discord.Color.green())\
									.add_field(name = "Birthday set to", value = f"{_months[month + 12].title()} {day}"), mention_author=False)
				else:
					await message.reply(embed = discord.Embed(title = "bday Command", description = "Use `bday` **<**`month`**>** **<**`day`**>**", color = discord.Color.dark_blue())\
						.add_field(name = "month", value = "The month can be a three letter abbreviation (Jan, Feb, Nov, or Dec), full names (April, August, September, or July), or a number (3, 5, 6, or 10)", inline = False)\
						.add_field(name = "day", value = "The day must be a number (1 to 28/29/30/31)", inline = False), mention_author=False)

			elif cmd == "chaos":
				if args.__len__():
					subcommand = args[0].lower()
					args = args[1:]

					if subcommand == "balance":
						await message.reply(embed = discord.Embed(title = "chaos balance Command", description = f"Your balance is {self.get_balance(message.author.id)}", color = discord.Color.green()), mention_author=False)

					elif subcommand == "post":
						balance = self.get_balance(message.author.id)

						if balance < 50:
							await message.reply(embed = discord.Embed(title = "chaos post Command", description = "Insufficient funds", color = discord.Color.red())\
								.add_field(name = "It costs 50 chaos points to make a chaotic post", value = f"Your balance is {balance}"), mention_author=False)
						else:
							to_post = message.clean_content[11:]
							self.posts_to_confirm[message.author.id] = to_post

							await message.reply(embed = discord.Embed(title = "chaos post Command", description = "Confirm post", color = discord.Color.green())\
								.add_field(name = f"You'll have {balance - 50} chaos point{'' if (balance - 50) == 1 else 's'} left, confirm post below", value = f"{to_post}", inline = False)\
								.add_field(name = "Use `chaos confirm` to make this post", value = "This will take 50 chaos points", inline = False)\
								.add_field(name = "Use `chaos cancel` to cancel this post", value = "This will cancel this post", inline = False), mention_author=False)

					elif subcommand == "confirm":
						if message.author.id in self.posts_to_confirm:
							balance = self.get_balance(message.author.id)

							if balance < 50:
								del self.posts_to_confirm[message.author.id]
								await message.reply(embed = discord.Embed(title = "chaos confirm Command", description = "Insufficient funds", color = discord.Color.red())\
									.add_field(name = "It costs 50 chaos points to make a chaotic post", value = f"Your balance is {balance}"), mention_author=False)
							else:
								chaos_channel: discord.TextChannel = self.get_channel(self.chaos_channel_id)

								if chaos_channel is None:
									print(f"Unable to post to chaos channel, couldn't find channel with id \"{self.chaos_channel_id}\"")
									await message.reply(embed = discord.Embed(title = "chaos confirm Command", description = "Post failure", color = discord.Color.red())\
										.add_field(name = "Cannot post right now", value = "Unable to locate chaos text channel", inline = False), mention_author=False)

								else:
									post = self.posts_to_confirm[message.author.id]
									await chaos_channel.send(f"{post}")

									chaos_data = _read_json(self.chaos_file_path)
									chaos_data[str(message.author.id)]["chaos_posts"].append(post)
									_write_json(self.chaos_file_path, chaos_data)

									del self.posts_to_confirm[message.author.id]

									await message.reply(embed = discord.Embed(title = "chaos confirm Command", description = "Post confirmed", color = discord.Color.green()), mention_author=False)

									await self.update_leaderboard()
						else:
							await message.reply(embed = discord.Embed(title = "chaos confirm Command", description = "No post", color = discord.Color.dark_blue())\
								.add_field(name = "You need to attempt to make a post before you can confirm one", value = f"Use `chaos post <message>`"), mention_author=False)

					elif subcommand == "cancel":
						if message.author.id in self.posts_to_confirm:
							del self.posts_to_confirm[message.author.id]
							await message.reply(embed = discord.Embed(title = "chaos cancel Command", description = "Post cancelled", color = discord.Color.green()), mention_author=False)

						else:
							await message.reply(embed = discord.Embed(title = "chaos cancel Command", description = "No post", color = discord.Color.dark_blue())\
								.add_field(name = "You need to attempt to make a post before you can cancel one", value = f"Use `chaos post <message>`"), mention_author=False)

					else:
						await message.reply(embed = discord.Embed(title = "chaos Command", description = "Invalid subcommand", color = discord.Color.red())\
							.add_field(name = "balance", value = "Get your balance of chaos points", inline = False)\
							.add_field(name = "post", value = "Send a chaotic message at the cost of 50 chaos points", inline = False)\
							.add_field(name = "confirm", value = "Confirm to send a chaotic message", inline = False)\
							.add_field(name = "cancel", value = "Cancel the posting of a chaotic message", inline = False), mention_author=False)

				else:
					await message.reply(embed = discord.Embed(title = "chaos Command", description = "chaos subcommands:", color = discord.Color.dark_blue())\
						.add_field(name = "balance", value = "Get your balance of chaos points", inline = False)\
						.add_field(name = "post", value = "Send a chaotic message at the cost of 50 chaos points", inline = False)\
						.add_field(name = "confirm", value = "Confirm to send a chaotic message", inline = False)\
						.add_field(name = "cancel", value = "Cancel the posting of a chaotic message", inline = False), mention_author=False)

		else: # Managed, Guilds
			check = await self.check_message(message)

			if check == 1:
				if not edited: # Prevent infinite points from editing messages on Christmas or a birthday
					await self.increase_chaos(message.author.id, message.author.name)

			elif check == -1:
				await message.delete()

				if edited: # They would've gained chaos so take away chaos
					await self.decrease_chaos(message.author.id, message.author.name)
		
		self.update_last_online()

	async def on_message(self, message: discord.Message):
		await self.message_handle(message)

	async def on_message_edit(self, _, after_message: discord.Message):
		await self.message_handle(after_message, True)

	async def on_member_join(self, member: discord.member.Member):
		equal_role = discord.utils.get(member.guild.roles, id = self.equal_role_id) # Get Equal role

		if equal_role is None:
			print(f"Unable to assign Equal role as a role couldn't be found with id \"{self.equal_role_id}\"")
		else:
			await member.edit(nick = "Equal", roles = [equal_role], reason = "To make us all Equal") # Set nickname and roles

def main():
	config_path = os.path.join(_project_root, "config")
	if not os.path.isdir(config_path):
		os.makedirs(config_path, 0o744, True)

	bot_config_path = os.path.join(config_path, "bot.json")
	if not os.path.isfile(bot_config_path):
		_write_json(bot_config_path, {
			"Historical Search Threshold (in seconds)": 600,
			"Leaderboard Channel ID": None,
			"Equal Channel ID": None,
			"Equal Role ID": None,
			"Historical Purge": False
		}, True) # Write default config so we don't have to ship it

	data_path = os.path.join(_project_root, "data")
	if not os.path.isdir(data_path):
		os.makedirs(data_path, 0o744, True)

	birthdays_path = os.path.join(_project_root, "data", "birthdays.json")
	if not os.path.isfile(birthdays_path):
		_write_json(birthdays_path, {})

	dotenv.load_dotenv()

	if os.getenv("ClientSecret") is None:
		env_file_path = os.path.join(_project_root, "src", ".env")
		if os.path.isfile(env_file_path):
			with open(env_file_path, "a") as env_file:
				env_file.write("\nClientSecret=<bot secret token>")
		else:
			with open(env_file_path, "w") as env_file:
				env_file.write("ClientSecret=<bot secret token>")

		raise ValueError(f"Set the ClientSecret value inside of the .env file at {os.path.join(_project_root, 'src')} to your bot's secret token")

	if os.getenv("ClientSecret") == "<bot secret token>":
		raise ValueError(f"Set the ClientSecret value inside of the .env file at {os.path.join(_project_root, 'src')} to your bot's secret token")

	EqualBot().run(os.getenv("ClientSecret"))

if __name__ == "__main__": main()