"""
Discord commands and event listeners for shiritori functionality
"""
import os
import datetime
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

from game.shiritori_game import ShiritoriGame, GameState, GameType
from utils.gemini_client import get_gemini_client

# Load environment variables
load_dotenv()


class ShiritoriCog(commands.Cog):
    """Cog providing shiritori functionality"""
    
    def __init__(self, bot):
        self.bot = bot
        self.game = ShiritoriGame()
        self.gemini_client = get_gemini_client()
        self.shiritori_channel_id = int(os.getenv("SHIRITORI_CHANNEL_ID", 0))
    
    @app_commands.command(name="shiritori", description="しりとりコマンド")
    @app_commands.describe(
        action="実行するアクション",
        word="ゲーム開始時の最初の単語（goアクションでのみ使用）"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="start - ゲーム開始（参加者募集）", value="start"),
        app_commands.Choice(name="join - ゲームに参加", value="join"),
        app_commands.Choice(name="go - ゲーム本格開始", value="go"),
        app_commands.Choice(name="end - ゲーム終了", value="end"),
        app_commands.Choice(name="status - 状況確認", value="status"),
        app_commands.Choice(name="help - ヘルプ表示", value="help"),
    ])
    async def shiritori_command(
        self, 
        interaction: discord.Interaction, 
        action: str, 
        word: str = None
    ):
        """Main handler for shiritori command"""
        
        # チャンネル制限チェック
        if (self.shiritori_channel_id != 0 and 
            interaction.channel.id != self.shiritori_channel_id):
            await interaction.response.send_message(
                "このチャンネルではしりとりコマンドは使用できません。",
                ephemeral=True
            )
            return
        
        if action == "start":
            await self._handle_start(interaction)
        elif action == "join":
            await self._handle_join(interaction)
        elif action == "go":
            await self._handle_go(interaction, word)
        elif action == "end":
            await self._handle_end(interaction)
        elif action == "status":
            await self._handle_status(interaction)
        elif action == "help":
            await self._handle_help(interaction)
    
    async def _handle_start(self, interaction: discord.Interaction):
        """Game start processing"""
        if self.game.state != GameState.WAITING:
            await interaction.response.send_message(
                "既にゲームが開始されています。`/shiritori end`で終了してから新しいゲームを開始してください。",
                ephemeral=True
            )
            return
        
        self.game.reset()
        self.game.set_game_creator(interaction.user.id)
        embed = discord.Embed(
            title="🎯 しりとりゲーム開始！",
            description=(
                "参加者を募集中です！\n"
                "`/shiritori join`で参加してください。\n"
                "参加者が揃ったら`/shiritori go [最初の単語]`でゲーム開始！"
            ),
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📜 基本ルール",
            value=(
                "🔤 前の単語の最後の文字で始まる単語を答える\n"
                "🚫 一度使った単語は使用不可\n"
                "💀 「ん」で終わったら負け\n"
                "📖 実在する一般的な名詞のみ有効\n"
                "⏰ 順番を守って回答する"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🤖 AI検証システム",
            value=(
                "Gemini AIが単語を自動判定します\n"
                "✅ 一般的な名詞のみ受け入れ\n"
                "❌ 固有名詞・造語・俗語は除外"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📝 参加方法",
            value=(
                "1. `/shiritori join` で参加登録\n"
                "2. 2人以上集まったらゲーム開始可能\n"
                "3. `/shiritori go [最初の単語]` で開始"
            ),
            inline=False
        )
        
        embed.set_footer(text="💡 /help でより詳しい説明を見ることができます")
        
        await interaction.response.send_message(embed=embed)
    
    async def _handle_join(self, interaction: discord.Interaction):
        """ゲーム参加処理"""
        if self.game.state != GameState.WAITING:
            await interaction.response.send_message(
                "参加募集中ではありません。",
                ephemeral=True
            )
            return
        
        user_id = interaction.user.id
        if self.game.add_participant(user_id):
            participant_list = "\n".join([
                f"{i+1}. <@{uid}>" for i, uid in enumerate(self.game.participants)
            ])
            
            embed = discord.Embed(
                title="✅ 参加登録完了！",
                description=f"<@{user_id}>さんが参加しました！",
                color=discord.Color.blue()
            )
            embed.add_field(
                name=f"参加者 ({len(self.game.participants)}人)",
                value=participant_list,
                inline=False
            )
            
            if len(self.game.participants) >= 2:
                embed.add_field(
                    name="ゲーム開始可能！",
                    value="`/shiritori go [最初の単語]`でゲームを開始できます。",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(
                "既に参加済みです。",
                ephemeral=True
            )
    
    async def _handle_go(self, interaction: discord.Interaction, first_word: str):
        """ゲーム本格開始処理"""
        if not self.game.is_game_creator(interaction.user.id):
            await interaction.response.send_message(
                "ゲーム開始は、ゲームを作成したユーザーのみが実行できます。",
                ephemeral=True
            )
            return
            
        if self.game.state != GameState.WAITING:
            await interaction.response.send_message(
                "ゲームを開始できる状態ではありません。",
                ephemeral=True
            )
            return
        
        if len(self.game.participants) < 2:
            await interaction.response.send_message(
                "参加者が2人以上必要です。",
                ephemeral=True
            )
            return
        
        if not first_word:
            await interaction.response.send_message(
                "最初の単語を指定してください。例: `/shiritori go りんご`",
                ephemeral=True
            )
            return
        
        first_word = first_word.strip()
        
        # 単語形式の検証
        is_valid_format, format_error = self.game.is_valid_word_format(first_word)
        if not is_valid_format:
            await interaction.response.send_message(
                f"❌ {format_error}",
                ephemeral=True
            )
            return
        
        # 「ん」で終わっていないかチェック
        if first_word.endswith('ん'):
            await interaction.response.send_message(
                "「ん」で終わる単語は使用できません。",
                ephemeral=True
            )
            return
        
        # Gemini APIで単語を検証
        await interaction.response.defer()
        
        try:
            is_valid, reason = await self.gemini_client.validate_word(first_word)
            
            if not is_valid:
                await interaction.followup.send(
                    f"「{first_word}」は使用できません。\n理由: {reason}",
                    ephemeral=True
                )
                return
        except Exception as e:
            # API エラーの場合は警告付きで続行
            print(f"Gemini API エラー: {e}")
        
        # ゲーム開始
        if self.game.start_game(first_word, interaction.channel.id):
            first_player = self.game.get_current_player()
            next_char = first_word[-1]
            
            embed = discord.Embed(
                title="🚀 しりとりゲーム開始！",
                description=f"最初の単語: **{first_word}**",
                color=discord.Color.gold()
            )
            
            embed.add_field(
                name="🎯 次の番",
                value=(
                    f"<@{first_player}>さん\n"
                    f"「**{next_char}**」で始まる単語をチャットに投稿してください！"
                ),
                inline=False
            )
            
            participant_list = "\n".join([
                f"{i+1}. {'🎯' if i == 0 else '⭕'} <@{uid}>" 
                for i, uid in enumerate(self.game.participants)
            ])
            embed.add_field(
                name="👥 参加者順序",
                value=participant_list,
                inline=False
            )
            
            embed.add_field(
                name="📝 注意事項",
                value=(
                    "• 順番を守って単語を投稿してください\n"
                    "• Gemini AIが単語を自動で検証します\n"
                    "• 無効な単語は自動で拒否されます"
                ),
                inline=False
            )
            
            embed.set_footer(text="🎮 ゲーム開始！ 頑張って！")
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(
                "ゲームの開始に失敗しました。",
                ephemeral=True
            )
    
    async def _handle_end(self, interaction: discord.Interaction):
        """ゲーム終了処理"""
        if self.game.state == GameState.WAITING:
            await interaction.response.send_message(
                "進行中のゲームがありません。",
                ephemeral=True
            )
            return
        
        if not self.game.is_game_creator(interaction.user.id):
            await interaction.response.send_message(
                "ゲーム終了は、ゲームを作成したユーザーのみが実行できます。",
                ephemeral=True
            )
            return
        
        self.game.end_game()
        
        embed = discord.Embed(
            title="⏹️ ゲーム強制終了",
            description="しりとりゲームが管理者により終了されました。",
            color=discord.Color.red()
        )
        
        if self.game.start_time:
            embed.add_field(
                name="📊 ゲーム統計",
                value=(
                    f"🔢 使用された単語数: **{len(self.game.used_words)}個**\n"
                    f"👥 参加者数: **{len(self.game.participants)}人**\n"
                    f"⏱️ ゲーム時間: <t:{int(self.game.start_time.timestamp())}:R>から"
                ),
                inline=False
            )
        
        if self.game.used_words:
            recent_words = " → ".join(self.game.used_words[-5:])
            embed.add_field(
                name="🔄 最近の単語（最新5個）",
                value=recent_words,
                inline=False
            )
        
        embed.add_field(
            name="🎮 新しいゲーム",
            value="`/shiritori start` で新しいゲームを開始できます",
            inline=False
        )
        
        embed.set_footer(text="💡 /help でボットの使い方を確認できます")
        
        await interaction.response.send_message(embed=embed)
    
    async def _handle_status(self, interaction: discord.Interaction):
        """状況確認処理"""
        status = self.game.get_game_status()
        
        if status["state"] == "waiting":
            embed = discord.Embed(
                title="📊 ゲーム状況",
                description="🟡 参加者募集中",
                color=discord.Color.blue()
            )
            if self.game.participants:
                participant_list = "\n".join([
                    f"{i+1}. <@{uid}>" for i, uid in enumerate(self.game.participants)
                ])
                embed.add_field(
                    name=f"👥 参加者 ({len(self.game.participants)}人)",
                    value=participant_list,
                    inline=False
                )
                embed.add_field(
                    name="📝 次のステップ",
                    value="`/shiritori go [最初の単語]` でゲームを開始できます",
                    inline=False
                )
            else:
                embed.add_field(
                    name="📝 参加方法",
                    value="`/shiritori join` でゲームに参加してください",
                    inline=False
                )
        
        elif status["state"] == "in_progress":
            embed = discord.Embed(
                title="📊 ゲーム状況",
                description="🟢 ゲーム進行中",
                color=discord.Color.green()
            )
            embed.add_field(
                name="📝 現在の単語",
                value=f"**{status['current_word']}**",
                inline=True
            )
            embed.add_field(
                name="🔤 次の文字",
                value=f"「**{status['next_char']}**」で始まる単語",
                inline=True
            )
            embed.add_field(
                name="👤 現在の回答者",
                value=f"<@{status['current_player']}>",
                inline=True
            )
            embed.add_field(
                name="📊 使用済み単語数",
                value=f"{status['used_words_count']}個",
                inline=True
            )
            embed.add_field(
                name="👥 参加者数",
                value=f"{len(self.game.participants)}人",
                inline=True
            )
            embed.add_field(
                name="⏱️ ゲーム開始時刻",
                value=f"<t:{int(status['start_time'].timestamp())}:R>",
                inline=True
            )
            
            if len(self.game.used_words) > 1:
                recent_words = " → ".join(self.game.used_words[-5:])
                embed.add_field(
                    name="🔄 最近の単語（最新5個）",
                    value=recent_words,
                    inline=False
                )
            
            # 参加者リスト
            participant_list = "\n".join([
                f"{'🎯' if i == self.game.current_player_index else '⭕'} <@{uid}>" 
                for i, uid in enumerate(self.game.participants)
            ])
            embed.add_field(
                name="👥 参加者順序",
                value=participant_list,
                inline=False
            )
        
        else:
            embed = discord.Embed(
                title="📊 ゲーム状況",
                description="🔴 ゲーム終了",
                color=discord.Color.red()
            )
            embed.add_field(
                name="📝 新しいゲームを開始",
                value="`/shiritori start` で新しいゲームを開始できます",
                inline=False
            )
        
        embed.set_footer(text="💡 /help でボットの詳細説明を見ることができます")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def _handle_help(self, interaction: discord.Interaction):
        """ヘルプ表示処理"""
        embed = discord.Embed(
            title="📖 しりとりボット ヘルプ",
            description="Gemini AIが単語を検証するしりとりゲームです！",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="🎮 コマンド一覧",
            value=(
                "`/shiritori start` - ゲーム開始（参加者募集）\n"
                "`/shiritori join` - ゲームに参加\n"
                "`/shiritori go [単語]` - ゲーム本格開始\n"
                "`/shiritori end` - ゲーム終了\n"
                "`/shiritori status` - 現在の状況確認\n"
                "`/shiritori help` - このヘルプを表示\n"
                "`/help` - ボットの詳細説明を表示"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📜 ルール",
            value=(
                "• 前の単語の最後の文字で始まる単語を答える\n"
                "• 一度使った単語は使用不可\n"
                "• 「ん」で終わったら負け\n"
                "• 実在する一般的な名詞のみ有効\n"
                "• 順番を守って回答する"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🤖 AI検証",
            value=(
                "Gemini AIが以下をチェックします：\n"
                "• 単語が実在するか\n"
                "• 一般的な名詞かどうか\n"
                "• 固有名詞や造語ではないか"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="help", description="しりとりボットの詳細説明を表示")
    async def help_command(self, interaction: discord.Interaction):
        """ボットの詳細説明コマンド"""
        
        # メインのヘルプEmbed
        main_embed = discord.Embed(
            title="🎯 しりとり管理ボット",
            description=(
                "**Gemini AI搭載の高機能しりとりボット**\n\n"
                "このボットは、Google Gemini AIを使用してしりとりゲームを管理し、"
                "単語の妥当性を自動で判定する革新的なDiscordボットです。"
            ),
            color=discord.Color.gold()
        )
        
        main_embed.set_thumbnail(url="https://cdn.discordapp.com/embed/avatars/0.png")
        
        # 機能紹介
        features_embed = discord.Embed(
            title="✨ 主な機能",
            color=discord.Color.blue()
        )
        
        features_embed.add_field(
            name="🤖 AI単語検証",
            value=(
                "Gemini AIが投稿された単語を自動判定\n"
                "• 実在する単語かどうか\n"
                "• 一般的な名詞かどうか\n"
                "• 固有名詞・造語の除外"
            ),
            inline=True
        )
        
        features_embed.add_field(
            name="👥 マルチプレイヤー",
            value=(
                "複数人での対戦に対応\n"
                "• 参加者の順番管理\n"
                "• 自動での次プレイヤー指名\n"
                "• リアルタイム状況表示"
            ),
            inline=True
        )
        
        features_embed.add_field(
            name="📜 完全ルール実装",
            value=(
                "しりとりの全ルールを実装\n"
                "• 文字の繋がりチェック\n"
                "• 既出単語の管理\n"
                "• 「ん」終わり判定"
            ),
            inline=True
        )
        
        # 使い方ガイド
        usage_embed = discord.Embed(
            title="🎮 使い方ガイド",
            color=discord.Color.green()
        )
        
        usage_embed.add_field(
            name="1️⃣ ゲーム開始",
            value=(
                "`/shiritori start`\n"
                "参加者の募集を開始します"
            ),
            inline=False
        )
        
        usage_embed.add_field(
            name="2️⃣ ゲーム参加",
            value=(
                "`/shiritori join`\n"
                "開始されたゲームに参加します"
            ),
            inline=False
        )
        
        usage_embed.add_field(
            name="3️⃣ ゲーム本格開始",
            value=(
                "`/shiritori go [最初の単語]`\n"
                "例: `/shiritori go りんご`\n"
                "実際のしりとりを開始します"
            ),
            inline=False
        )
        
        usage_embed.add_field(
            name="4️⃣ 単語投稿",
            value=(
                "順番に従ってチャットに単語を投稿\n"
                "AIが自動で検証し、結果を表示します"
            ),
            inline=False
        )
        
        # ルール詳細
        rules_embed = discord.Embed(
            title="📋 ルール詳細",
            color=discord.Color.orange()
        )
        
        rules_embed.add_field(
            name="基本ルール",
            value=(
                "🔤 前の単語の最後の文字で始まる\n"
                "🚫 一度使った単語は使用不可\n"
                "💀 「ん」で終わったら負け\n"
                "📖 実在する一般的な名詞のみ\n"
                "⏰ 順番を守って回答"
            ),
            inline=True
        )
        
        rules_embed.add_field(
            name="AI判定基準",
            value=(
                "✅ 辞書に載っている一般名詞\n"
                "❌ 固有名詞（人名・地名など）\n"
                "❌ ブランド名・商品名\n"
                "❌ 略語・造語\n"
                "❌ 俗語・スラング"
            ),
            inline=True
        )
        
        rules_embed.add_field(
            name="勝敗条件",
            value=(
                "🏆 他の全プレイヤーが脱落\n"
                "💀 「ん」で終わる単語を使用\n"
                "❌ 無効な単語を使用\n"
                "⏰ 制限時間内に回答しない\n"
                "🔄 既出単語を使用"
            ),
            inline=False
        )
        
        # コマンド一覧
        commands_embed = discord.Embed(
            title="🛠️ コマンド一覧",
            color=discord.Color.purple()
        )
        
        commands_embed.add_field(
            name="ゲーム管理",
            value=(
                "`/shiritori start` - ゲーム開始\n"
                "`/shiritori join` - ゲーム参加\n"
                "`/shiritori go [単語]` - 本格開始\n"
                "`/shiritori end` - ゲーム終了"
            ),
            inline=True
        )
        
        commands_embed.add_field(
            name="情報確認",
            value=(
                "`/shiritori status` - 現在の状況\n"
                "`/shiritori help` - 基本ヘルプ\n"
                "`/help` - 詳細説明（このページ）"
            ),
            inline=True
        )
        
        # 技術情報
        tech_embed = discord.Embed(
            title="🔧 技術情報",
            color=discord.Color.dark_grey()
        )
        
        tech_embed.add_field(
            name="使用技術",
            value=(
                "🐍 Python 3.10+\n"
                "🤖 Discord.py 2.3+\n"
                "🧠 Google Gemini AI\n"
                "⚡ 非同期処理対応"
            ),
            inline=True
        )
        
        tech_embed.add_field(
            name="機能",
            value=(
                "📊 リアルタイム状況表示\n"
                "💾 ゲーム履歴管理\n"
                "🔒 チャンネル制限機能\n"
                "🛡️ エラーハンドリング"
            ),
            inline=True
        )
        
        tech_embed.add_field(
            name="サポート",
            value=(
                "24時間安定稼働\n"
                "高速AI応答（2秒以内）\n"
                "複数ゲーム同時対応\n"
                "定期的なアップデート"
            ),
            inline=False
        )
        
        # フッター情報
        main_embed.set_footer(
            text="💡 ヒント: /shiritori start でゲームを開始できます！",
            icon_url="https://cdn.discordapp.com/embed/avatars/1.png"
        )
        
        # Embedを順番に送信
        await interaction.response.send_message(embed=main_embed)
        await interaction.followup.send(embed=features_embed)
        await interaction.followup.send(embed=usage_embed)
        await interaction.followup.send(embed=rules_embed)
        await interaction.followup.send(embed=commands_embed)
        await interaction.followup.send(embed=tech_embed)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Message monitoring (shiritori word input)"""
        # Ignore bot's own messages
        if message.author.bot:
            return
        
        # Ignore channels other than specified channel
        if (self.shiritori_channel_id != 0 and 
            message.channel.id != self.shiritori_channel_id):
            return
        
        # Ignore commands
        if message.content.startswith('/'):
            return
        
        # Ignore if game is not in progress (check both normal and association versions)
        normal_game_active = self.game.state == GameState.IN_PROGRESS
        association_game_active = (hasattr(self, 'association_game') and 
                                 self.association_game is not None and 
                                 self.association_game.state == GameState.IN_PROGRESS)
        
        if not normal_game_active and not association_game_active:
            return
        
        # Determine which game is in progress
        if association_game_active:
            await self._handle_association_word(message)
        elif normal_game_active:
            await self._handle_normal_word(message)
    
    async def _handle_normal_word(self, message: discord.Message):
        """Normal shiritori word processing"""
        # Extract word from message
        word = message.content.strip()
        if not word:
            return
        
        user_id = message.author.id
        
        # Validate word format
        is_valid_format, format_error = self.game.is_valid_word_format(word)
        if not is_valid_format:
            await message.reply(f"❌ {format_error}")
            return
        
        # First, basic rule check
        result = self.game.submit_word(user_id, word)
        
        if not result["success"] and "順番" not in result["message"]:
            # For errors other than turn errors
            await message.reply(result["message"])
            return
        elif not result["success"]:
            # Silently ignore turn errors
            return
        
        # Validate word with Gemini API
        try:
            is_valid, reason = await self.gemini_client.validate_word(word)
            
            if not is_valid:
                # If invalid word, revert game state
                # (For simple implementation, remove from used words)
                if word in self.game.used_words:
                    self.game.used_words.remove(word)
                    self.game.current_word = self.game.used_words[-1] if self.game.used_words else None
                    # Also revert player index
                    self.game.current_player_index = (self.game.current_player_index - 1) % len(self.game.participants)
                
                await message.reply(f"❌ 「{word}」は使用できません。\n理由: {reason}")
                return
                
        except Exception as e:
            # Continue with warning in case of API error
            print(f"Gemini API error: {e}")
            await message.add_reaction("⚠️")
        
        # Processing on success
        if result["game_ended"]:
            embed = discord.Embed(
                title="🏁 ゲーム終了！",
                description=result["message"],
                color=discord.Color.red()
            )
            
            # Game statistics
            embed.add_field(
                name="📊 Game Statistics",
                value=(
                    f"🔢 使用された単語数: **{len(self.game.used_words)}個**\n"
                    f"👥 参加者数: **{len(self.game.participants)}人**\n"
                    f"⏱️ ゲーム時間: <t:{int(self.game.start_time.timestamp())}:R>から"
                ),
                inline=False
            )
            
            # Participant list
            if self.game.participants:
                participant_list = "\n".join([
                    f"{'💀' if uid == result.get('loser') else '👤'} <@{uid}>" 
                    for uid in self.game.participants
                ])
                embed.add_field(
                    name="👥 Participants",
                    value=participant_list,
                    inline=True
                )
            
            if len(self.game.used_words) > 1:
                word_chain = " → ".join(self.game.used_words)
                if len(word_chain) > 1000:  # Discord limit countermeasure
                    word_chain = " → ".join(self.game.used_words[-10:]) + "\n*(Only last 10 shown)*"
                embed.add_field(
                    name="🔄 Word Flow",
                    value=word_chain,
                    inline=False
                )
            
            embed.add_field(
                name="🎮 New Game",
                value="`/shiritori start` to start a new game",
                inline=False
            )
            
            embed.set_footer(text="Good work! 🎉")
            
            await message.reply(embed=embed)
        else:
            await message.reply(f"✅ {result['message']}")
            await message.add_reaction("✅")
    
    async def _handle_association_word(self, message: discord.Message):
        """Association shiritori word processing"""
        # Extract word from message
        word = message.content.strip()
        if not word:
            return
        
        user_id = message.author.id
        
        # Validate word format
        is_valid_format, format_error = self.association_game.is_valid_word_format(word)
        if not is_valid_format:
            await message.reply(f"❌ {format_error}")
            return
        
        # Basic rule check for association version (no character connection required)
        # Turn check
        if user_id != self.association_game.get_current_player():
            return  # Silently ignore if not their turn
        
        # Duplicate check
        if word in self.association_game.used_words:
            await message.reply("❌ その単語は既に使用されています。")
            return
        
        # Validate word validity and association appropriateness with Gemini API
        try:
            previous_word = self.association_game.current_word
            
            # Check if word is valid
            is_valid, reason = await self.gemini_client.validate_word(word)
            if not is_valid:
                await message.reply(f"❌ 「{word}」は使用できません。\n理由: {reason}")
                return
            
            # Check if association is appropriate with Gemini API
            association_prompt = (
                f"「{previous_word}」から「{word}」への連想は適切ですか？"
                f"連想しりとりのルールに従って判定してください。"
                f"適切な場合は「YES」、不適切な場合は「NO: 理由」で答えてください。"
            )
            
            association_result = await self.gemini_client.validate_association(previous_word, word)
            
            if not association_result["valid"]:
                await message.reply(f"❌ 「{previous_word}」→「{word}」の連想が不適切です。\n理由: {association_result['reason']}")
                return
                
        except Exception as e:
            # Continue with warning in case of API error
            print(f"Gemini API error: {e}")
            await message.add_reaction("⚠️")
        
        # submit_word processing for association version (no character connection check)
        self.association_game.used_words.append(word)
        self.association_game.current_word = word
        
        # Add to game history
        self.association_game.game_history.append({
            "player": user_id,
            "word": word,
            "timestamp": datetime.datetime.now()
        })
        
        # Move to next player
        self.association_game.current_player_index = ((self.association_game.current_player_index + 1) % 
                                                    len(self.association_game.participants))
        next_player = self.association_game.get_current_player()
        
        # Success message
        embed = discord.Embed(
            title="✅ Association Success!",
            description=f"「{previous_word}」→「{word}」",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="🎯 Next Player",
            value=f"<@{next_player}>",
            inline=True
        )
        
        embed.add_field(
            name="💭 Association Hint",
            value=f"Think of words associated with 「{word}」!",
            inline=False
        )
        
        await message.reply(embed=embed)
        await message.add_reaction("✅")
    
    @app_commands.command(name="renso-shiritori", description="連想しりとりコマンド")
    @app_commands.describe(
        action="実行するアクション",
        word="ゲーム開始時の最初の単語（goアクションでのみ使用）"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="start - ゲーム開始（参加者募集）", value="start"),
        app_commands.Choice(name="join - ゲームに参加", value="join"),
        app_commands.Choice(name="go - ゲーム本格開始", value="go"),
        app_commands.Choice(name="end - ゲーム終了", value="end"),
        app_commands.Choice(name="status - 状況確認", value="status"),
        app_commands.Choice(name="help - ヘルプ表示", value="help"),
    ])
    async def renso_shiritori_command(
        self, 
        interaction: discord.Interaction, 
        action: str, 
        word: str = None
    ):
        """連想しりとりコマンドのメインハンドラー"""
        # 連想版用のゲームインスタンスを作成（必要に応じて）
        if not hasattr(self, 'association_game') or self.association_game is None:
            self.association_game = ShiritoriGame(GameType.ASSOCIATION)
        
        # 一時的にゲームインスタンスを切り替える
        original_game = self.game
        self.game = self.association_game
        
        try:
            # 通常のしりとりコマンドと同じ処理を実行
            if action == "start":
                await self._handle_start_association(interaction)
            elif action == "join":
                await self._handle_join(interaction)
            elif action == "go":
                await self._handle_go_association(interaction, word)
            elif action == "end":
                await self._handle_end(interaction)
            elif action == "status":
                await self._handle_status_association(interaction)
            elif action == "help":
                await self._handle_help_association(interaction)
        finally:
            # ゲームインスタンスを元に戻す
            self.association_game = self.game
            self.game = original_game
    
    async def _handle_start_association(self, interaction: discord.Interaction):
        """連想版ゲーム開始処理"""
        if self.game.state != GameState.WAITING:
            await interaction.response.send_message(
                "既にゲームが開始されています。`/renso-shiritori end`で終了してから新しいゲームを開始してください。",
                ephemeral=True
            )
            return
        
        self.game.reset()
        self.game.set_game_creator(interaction.user.id)
        embed = discord.Embed(
            title="🎯 連想しりとりゲーム開始！",
            description=(
                "参加者を募集中です！\n"
                "`/renso-shiritori join`で参加してください。\n"
                "参加者が揃ったら`/renso-shiritori go [最初の単語]`でゲーム開始！"
            ),
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="📜 連想しりとりのルール",
            value=(
                "• 前の単語から**連想**される単語を答える\n"
                "• 「りんご」→「赤」→「トマト」のように関連する言葉をつなげる\n"
                "• 文字の最後で繋がる必要はありません\n"
                "• 同じ単語は2回使用できません\n"
                "• 適切な連想でない場合は無効になります"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💡 参加方法",
            value="`/renso-shiritori join`",
            inline=True
        )
        
        embed.add_field(
            name="🎮 ゲーム開始",
            value="`/renso-shiritori go [最初の単語]`",
            inline=True
        )
        
        embed.set_footer(text="連想の幅を広げて楽しもう！")
        
        await interaction.response.send_message(embed=embed)
    
    async def _handle_go_association(self, interaction: discord.Interaction, first_word: str):
        """連想版ゲーム本格開始処理"""
        if not self.game.is_game_creator(interaction.user.id):
            await interaction.response.send_message(
                "ゲーム開始は、ゲームを作成したユーザーのみが実行できます。",
                ephemeral=True
            )
            return
            
        if self.game.state != GameState.WAITING:
            await interaction.response.send_message(
                "ゲームを開始できる状態ではありません。",
                ephemeral=True
            )
            return
        
        if len(self.game.participants) < 2:
            await interaction.response.send_message(
                "参加者が2人以上必要です。",
                ephemeral=True
            )
            return
        
        if not first_word:
            await interaction.response.send_message(
                "最初の単語を指定してください。例: `/renso-shiritori go りんご`",
                ephemeral=True
            )
            return
        
        first_word = first_word.strip()
        
        # 単語形式の検証
        is_valid_format, format_error = self.game.is_valid_word_format(first_word)
        if not is_valid_format:
            await interaction.response.send_message(
                f"❌ {format_error}",
                ephemeral=True
            )
            return
        
        # Gemini APIで単語を検証
        await interaction.response.defer()
        
        try:
            is_valid, reason = await self.gemini_client.validate_word(first_word)
            
            if not is_valid:
                await interaction.followup.send(
                    f"❌ 「{first_word}」は使用できません。\n理由: {reason}",
                    ephemeral=True
                )
                return
        except Exception as e:
            await interaction.followup.send(
                f"❌ 単語の検証でエラーが発生しました: {str(e)}",
                ephemeral=True
            )
            return
        
        # ゲーム開始
        self.game.start_game(first_word)
        
        embed = discord.Embed(
            title="🎉 連想しりとりゲームスタート！",
            description=f"最初の単語: **{first_word}**",
            color=discord.Color.green()
        )
        
        current_player = self.game.get_current_player()
        embed.add_field(
            name="🎯 現在のプレイヤー",
            value=f"<@{current_player}>さん",
            inline=True
        )
        
        embed.add_field(
            name="💭 次の単語のヒント",
            value=f"「{first_word}」から連想される言葉を考えてください！",
            inline=False
        )
        
        participant_list = "\n".join([f"<@{p}>" for p in self.game.participants])
        embed.add_field(
            name=f"👥 参加者 ({len(self.game.participants)}人)",
            value=participant_list,
            inline=False
        )
        
        embed.set_footer(text="チャットに単語を入力してください！")
        
        await interaction.followup.send(embed=embed)
    
    async def _handle_status_association(self, interaction: discord.Interaction):
        """連想版ステータス表示処理"""
        status = self.game.get_status()
        
        if status["state"] == "waiting":
            embed = discord.Embed(
                title="📊 連想しりとりゲーム状況",
                description="現在、参加者を募集中です。",
                color=discord.Color.blue()
            )
            if status["participants_count"] > 0:
                participant_list = "\n".join([f"<@{p}>" for p in self.game.participants])
                embed.add_field(
                    name=f"参加者 ({status['participants_count']}人)",
                    value=participant_list,
                    inline=False
                )
        elif status["state"] == "in_progress":
            embed = discord.Embed(
                title="📊 連想しりとりゲーム進行状況",
                description="ゲーム進行中！",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="🎯 現在のプレイヤー",
                value=f"<@{status['current_player']}>",
                inline=True
            )
            
            embed.add_field(
                name="📝 現在の単語",
                value=f"**{status['current_word']}**",
                inline=True
            )
            
            embed.add_field(
                name="🔢 使用済み単語数",
                value=f"{status['used_words_count']}個",
                inline=True
            )
            
            if len(self.game.used_words) > 1:
                recent_words = " → ".join(self.game.used_words[-5:])
                embed.add_field(
                    name="📚 最近の単語（最大5個）",
                    value=recent_words,
                    inline=False
                )
        else:
            embed = discord.Embed(
                title="📊 連想しりとりゲーム状況",
                description="現在進行中のゲームはありません。",
                color=discord.Color.gray()
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def _handle_help_association(self, interaction: discord.Interaction):
        """連想版ヘルプ表示処理"""
        embed = discord.Embed(
            title="🎮 連想しりとりBot ヘルプ",
            description="連想でつなぐしりとりゲームの説明です",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="🎯 ゲームの目的",
            value=(
                "前の単語から**連想**される単語をつなげていく言葉遊びです。\n"
                "文字ではなく、意味や関連性でつながります。"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📜 基本ルール",
            value=(
                "• 前の単語から連想される言葉を答える\n"
                "• 同じ単語は使用できません\n"
                "• 連想が適切でない場合は無効\n"
                "• 順番は自動で管理されます"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💡 連想の例",
            value=(
                "「りんご」→「赤」→「トマト」→「野菜」→「健康」\n"
                "「海」→「青」→「空」→「雲」→「雨」"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🎮 コマンド一覧",
            value=(
                "`/renso-shiritori start` - ゲーム開始（参加者募集）\n"
                "`/renso-shiritori join` - ゲームに参加\n"
                "`/renso-shiritori go [単語]` - ゲーム本格開始\n"
                "`/renso-shiritori status` - 現在の状況確認\n"
                "`/renso-shiritori end` - ゲーム終了\n"
                "`/renso-shiritori help` - このヘルプを表示"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🎲 ゲームの流れ",
            value=(
                "1. `/renso-shiritori start`でゲーム作成\n"
                "2. 他の人が`/renso-shiritori join`で参加\n"
                "3. 作成者が`/renso-shiritori go [単語]`で開始\n"
                "4. チャットに連想した単語を入力\n"
                "5. 順番に連想単語をつなげていく"
            ),
            inline=False
        )
        
        embed.set_footer(text="連想の幅を広げて楽しみましょう！")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    """Function to add Cog to bot"""
    await bot.add_cog(ShiritoriCog(bot))
