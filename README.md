# EqualBot

### A bot to bring true equality

<br>

## How to install

Have `git`, `python3`, and `pip3` install from your local package manager.

```bash
# Clone repo
git clone https://github.com/5Dev24/EqualBot

# Move into repo
cd ./EqualBot/

# Change virtual environment
python3 -m venv ./venv/

# Active virtual environment
source ./venv/bin/active

# Install python dependencies
pip3 install -r ./requirements.txt

# While the bot's code is installed, it will not yet run. Follow the setup steps below to get it working
```

<br>

## How to setup

### Setting the bot's token

```bash
# This step can be skipped so long as the environement variable ClientSecret is set to your bot's secret token

# Run initially to generate setup files
# Should terminate with a message telling you to set your bot's secret token
python3 ./src/__main__.py

# Get your bot's secret token

# Replace "[PLACE YOUR TOKEN HERE]" with your bot's secret token
echo "ClientSecret=[PLACE YOUR TOKEN HERE]" > ./src/.env
```

<br>

### Configuring the bot to your server

You'll need to have enable `Developer Mode` on Discord in order to view the ids of everything. 
To enable it, go to  `User Settings` > `Advanced` > `Developer Mode` and turn it on.

```bash
# Use your favorite GUI or command line text editor for these next few steps
# I'll be using nano as an example

nano ./config/bot.json
```

<br>

Right click on the text channel you want to have as the leaderboard and copy it's id

Find the line that contains: "Leaderboard Channel ID": null

Replace the null with the channel id for the leaderboard channel (leave the comma that comes after the null)

<br>

Right click on the text channel you want to have as the equal channel and copy it's id

Find the line that contains: "Equal Channel ID": null

Replace the null with the channel id for the equal channel (leave the comma that comes after the null)

<br>

Next you'll need your equal role, this can be used to prevent people from reacting, sending tts, adding attachments, etc. You can find my roles at the end of this guide. Note that the server only has this bot running on it.

Go to Server Settings > Roles, right click on the role you want for the equal role and copy it's id

Note: this role will be given to all people that join the server but not those who are already in the server

Find the line that contains: "Equal Role ID": null

Replace the null with the role id for the equal role (leave the comma that comes after the null)

```bash
# Now save and close nano by pressing Ctrl + X, then Ctrl + Y, and pressing Enter
```

### Running the bot

I don't recommend a docker or any containerization because a virtual python environment should isolate it package wise from the system.

```bash
# Active virtual environment
source ./venv/bin/active

# Run bot
python3 ./src/__main__.py

# or, because the Python3 env shebang at the top of the file
./src/__main__.py # If you can't run it, use `chmod +x ./src/__main__.py` to make the file executable
```

I used the following script to start mine. The main thing is to remember to have the bash shebang else you'll run into issues with it saying that `source` cannot being found.

```bash
#!/bin/bash
source ./venv/bin/active
python3 ./src/__main__.py
```

Also running this as a sevice works so you don't have to manually start it everytime your server comes back online. Example below is mine.

```
[Unit]
Description=EqualBot
After=network.target
StartLimitBurst=3
StartLimitIntervalSec=20

[Service]
WorkingDirectory=/opt/EqualBot/
ExecStart=/bin/bash /opt/EqualBot/start.sh
Restart=on-failure
RestartSec=3s

[Install]
WantedBy=multi-user.target
```

### Congratulations

You've install, setup, configured, and ran the bot!

Welcome to true equality

## My Discord Setup

(If I list it then it's turned on, if not, I have it off)

Roles:
* Equal (Bot role)
	- `Administrator`

* Equal (User role)
	- `Display role members separately...`
	- `View Channels`
	- `Create Invite`
	- `Send Messages`
	- `Read Message History`

* Muted
	- `View Channels`
	- `Create Invite`
	- `Read Message History`

* @everyone
	(nothing, no permissions set)

Channels:
* Equal (category)
	- #equal (text channel)

* Chaos (category)
	- #leaderboard (text channel)
		* No role can `Send Messages`