Lion Bot



A feature-rich Discord bot designed with modular cogs, fast performance, and easy deployment.

Built using Python and discord.py, with full support for hosting on Railway / Railpack.



🚀 Features



Modular cog system (cogs/)



Custom utilities (utils/)



Config-based setup (config.json)



Fast, scalable deployment on Railway



Easy to maintain and expand



📁 Project Structure

./

├── cogs/           # Bot commands + modules

├── data/           # Saved bot data

├── utils/          # Helper utilities

├── bot.py          # Main bot file

├── config.json     # Bot configuration (token, prefixes, etc)

├── start.sh        # Start script for Railway

├── requirements.txt

└── runtime.txt



⚙️ Installation

1\. Clone the repository

git clone <your\_repo\_url>

cd <your\_repo\_name>



2\. Install dependencies

pip install -r requirements.txt



3\. Configure your bot



Edit config.json:



{

&nbsp;   "token": "YOUR\_BOT\_TOKEN",

&nbsp;   "prefix": "!"

}





Or convert to .env if preferred.



▶️ Running the Bot Locally

python bot.py



🌐 Deploying on Railway

1\. Make sure these files exist:



start.sh



requirements.txt



runtime.txt



2\. Railway will automatically detect Python and run:

./start.sh



3\. Deploy using:



GitHub → Railway



Or upload your project manually



📝 Start Script (start.sh)

\#!/bin/bash

python3 bot.py



🤝 Contributing



Feel free to open issues or pull requests!



📜 License



This project is licensed under the MIT License.

