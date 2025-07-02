# 🎯 Shiritori Management Bot

A high-performance Shiritori management Discord bot using Gemini API and Discord.py.

## ✨ Features

- 🤖 **AI Word Validation**: Gemini AI automatically validates word appropriateness
- 👥 **Multiplayer**: Supports multiplayer shiritori games
- 📜 **Complete Rule Implementation**: Used word checking, "n" ending detection, etc.
- 🎮 **Slash Commands**: Intuitive command interface
- 📊 **Game Status Display**: Real-time game status monitoring

## 🚀 Setup

### 1. Requirements

- Python 3.8 or higher
- Discord Bot Token
- Google Gemini API Key

### 2. Installation

```bash
# Clone the repository
git clone <repository-url>
cd shiritori-bot

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Setup

Create a `.env` file and configure the following:

```env
# Discord Bot Token
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Discord Channel ID (Channel ID for shiritori)
SHIRITORI_CHANNEL_ID=your_channel_id_here

# Debug Mode (True/False)
DEBUG_MODE=True
```

### 4. Launch

```bash
python main.py
```

## 🎮 How to Use

### Basic Game Flow

1. **Start Game**: `/shiritori start` - Start recruiting participants
2. **Join**: `/shiritori join` - Join the game
3. **Begin Game**: `/shiritori go [first word]` - Start the actual game
4. **Word Input**: Post words in chat following turn order
5. **End Game**: Automatic end or `/shiritori end`

### Command List

| Command | Description |
|---------|-------------|
| `/shiritori start` | Start game (recruit participants) |
| `/shiritori join` | Join the game |
| `/shiritori go [word]` | Begin actual game |
| `/shiritori end` | End game |
| `/shiritori status` | Check current status |
| `/shiritori help` | Display basic help |
| `/help` | **Display detailed bot description** |

## 📜 Rules

- Answer with a word that starts with the last character of the previous word
- Cannot use words that have already been used
- Lose if you end with "ん" (n)
- Only valid common nouns are allowed (judged by Gemini AI)
- Follow turn order for responses

## 🏗️ Project Structure

```
shiritori-bot/
├── .env                  # Environment variables file
├── .gitignore            # Git ignore settings
├── requirements.txt      # Dependency libraries
├── main.py               # Main file
├── README.md             # This file
│
├── cogs/                 # Discord.py Cogs
│   ├── __init__.py
│   └── shiritori_cog.py  # Shiritori command implementation
│
├── game/                 # Game logic
│   ├── __init__.py
│   └── shiritori_game.py # Game state management
│
└── utils/                # Utilities
    ├── __init__.py
    └── gemini_client.py  # Gemini API client
```

## 🔧 Configuration

### Discord Bot Setup

1. Create a bot on [Discord Developer Portal](https://discord.com/developers/applications)
2. Configure required permissions:
   - `Send Messages`
   - `Use Slash Commands`
   - `Read Message History`
   - `Add Reactions`

### Gemini API Setup

1. Get an API key from [Google AI Studio](https://makersuite.google.com/)
2. Configure in `.env` file

## 🤝 Contributing

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Create a Pull Request

## 📝 License

This project is released under the MIT License.

## 🆘 Troubleshooting

### Common Issues

**Q: Bot doesn't respond**
- Check if Discord Bot Token is correctly configured
- Check if bot has joined the server
- Check if appropriate permissions are granted

**Q: Gemini API errors occur**
- Check if API key is correctly configured
- Check if API usage limits are exceeded

**Q: Slash commands don't appear**
- Check if command sync completed during bot startup
- Try restarting the Discord app

## 📧 Support

If you encounter issues, please report them in Issues.
