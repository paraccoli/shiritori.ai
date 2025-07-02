"""
Class for managing shiritori game state and rule validation
"""
import asyncio
from typing import List, Optional, Dict
from enum import Enum
import datetime
import re


class GameState(Enum):
    """Enum representing game state"""
    WAITING = "waiting"  # Recruiting participants
    IN_PROGRESS = "in_progress"  # Game in progress
    ENDED = "ended"  # Game ended


class GameType(Enum):
    """Enum representing game type"""
    NORMAL = "normal"  # Normal shiritori
    ASSOCIATION = "association"  # Association shiritori


class ShiritoriGame:
    """Class for managing shiritori game state and rules"""
    
    def __init__(self, game_type: GameType = GameType.NORMAL):
        self.state: GameState = GameState.WAITING
        self.game_type: GameType = game_type
        self.participants: List[int] = []  # Discord User IDs of participants
        self.current_player_index: int = 0
        self.used_words: List[str] = []
        self.current_word: Optional[str] = None
        self.game_history: List[Dict] = []  # Game history
        self.start_time: Optional[datetime.datetime] = None
        self.channel_id: Optional[int] = None
        self.game_creator: Optional[int] = None  # User ID of game creator
        
    def add_participant(self, user_id: int) -> bool:
        """
        Add a participant
        
        Args:
            user_id: Discord User ID of the participant
            
        Returns:
            bool: True if addition succeeded, False if failed
        """
        if self.state != GameState.WAITING:
            return False
            
        if user_id not in self.participants:
            self.participants.append(user_id)
            return True
        return False
    
    def start_game(self, first_word: str, channel_id: int) -> bool:
        """
        ゲームを開始する
        
        Args:
            first_word: 最初の単語
            channel_id: ゲームを行うチャンネルID
            
        Returns:
            bool: 開始に成功した場合True、失敗した場合False
        """
        if self.state != GameState.WAITING or len(self.participants) < 2:
            return False
            
        self.state = GameState.IN_PROGRESS
        self.current_word = first_word
        self.used_words.append(first_word)
        self.start_time = datetime.datetime.now()
        self.channel_id = channel_id
        self.current_player_index = 0
        
        # ゲーム履歴に記録
        self.game_history.append({
            "word": first_word,
            "user_id": None,  # システムによる最初の単語
            "timestamp": self.start_time
        })
        
        return True
    
    def get_current_player(self) -> Optional[int]:
        """
        現在の回答者のUser IDを取得する
        
        Returns:
            int: 現在の回答者のUser ID、ゲームが進行中でない場合はNone
        """
        if self.state != GameState.IN_PROGRESS or not self.participants:
            return None
        return self.participants[self.current_player_index]
    
    def is_valid_turn(self, user_id: int) -> bool:
        """
        指定されたユーザーが回答する順番かを確認する
        
        Args:
            user_id: 確認するUser ID
            
        Returns:
            bool: 順番が正しい場合True
        """
        return self.get_current_player() == user_id
    
    def is_valid_word_start(self, word: str) -> bool:
        """
        単語の始まりが前の単語の終わりと一致するかを確認する
        
        Args:
            word: チェックする単語
            
        Returns:
            bool: 条件を満たす場合True
        """
        if not self.current_word or not word:
            return False
            
        # ひらがなに変換して比較（簡易版）
        last_char = self.current_word[-1]
        first_char = word[0]
        
        # 「ー」「ん」などの特殊文字の処理
        if last_char == 'ー':
            if len(self.current_word) > 1:
                last_char = self.current_word[-2]
        
        return last_char.lower() == first_char.lower()
    
    def is_word_used(self, word: str) -> bool:
        """
        単語が既に使用されているかを確認する
        
        Args:
            word: チェックする単語
            
        Returns:
            bool: 既に使用されている場合True
        """
        return word.lower() in [w.lower() for w in self.used_words]
    
    def is_valid_word_format(self, word: str) -> tuple[bool, str]:
        """
        単語の形式が妥当かを確認する
        
        Args:
            word: チェックする単語
            
        Returns:
            tuple: (妥当性(bool), エラーメッセージ(str))
        """
        if not word or not word.strip():
            return False, "空の入力は無効です。"
        
        word = word.strip()
        
        # 複数の単語（スペースや句読点で区切られている）をチェック
        if re.search(r'[\s、。！？\.,!?]', word):
            return False, "一つの単語のみ入力してください。句読点や記号は使用できません。"
        
        # 英数字や記号が含まれていないかチェック
        if re.search(r'[a-zA-Z0-9]', word):
            return False, "日本語のひらがな・カタカナのみ使用できます。"
        
        # 一般的でない記号をチェック
        if re.search(r'[!@#$%^&*()_+=\[\]{}|;:"<>,.?/~`]', word):
            return False, "記号は使用できません。"
        
        # 長すぎる単語をチェック
        if len(word) > 20:
            return False, "単語が長すぎます（20文字以内）。"
        
        # 短すぎる単語をチェック
        if len(word) < 2:
            return False, "2文字以上の単語を入力してください。"
        
        return True, ""
    
    def set_game_creator(self, user_id: int):
        """
        ゲーム作成者を設定する
        
        Args:
            user_id: ゲーム作成者のUser ID
        """
        self.game_creator = user_id
    
    def ends_with_n(self, word: str) -> bool:
        """
        単語が「ん」で終わっているかを確認する
        
        Args:
            word: チェックする単語
            
        Returns:
            bool: 「ん」で終わっている場合True
        """
        return word.endswith('ん')
    
    def submit_word(self, user_id: int, word: str) -> Dict:
        """
        単語を提出し、結果を返す
        
        Args:
            user_id: 提出者のUser ID
            word: 提出された単語
            
        Returns:
            dict: 結果情報を含む辞書
        """
        result = {
            "success": False,
            "message": "",
            "game_ended": False,
            "winner": None,
            "loser": None
        }
        
        # ゲーム状態チェック
        if self.state != GameState.IN_PROGRESS:
            result["message"] = "ゲームが進行中ではありません。"
            return result
        
        # 順番チェック
        if not self.is_valid_turn(user_id):
            current_player = self.get_current_player()
            result["message"] = f"<@{current_player}>さんの順番です。"
            return result
        
        # 単語の基本チェック
        word = word.strip()
        if not word:
            result["message"] = "有効な単語を入力してください。"
            return result
        
        # しりとりルールチェック
        if not self.is_valid_word_start(word):
            result["message"] = f"「{self.current_word[-1]}」で始まる単語を入力してください。"
            return result
        
        if self.is_word_used(word):
            result["message"] = f"「{word}」は既に使用されています。"
            return result
        
        # 「ん」で終わっている場合
        if self.ends_with_n(word):
            self.state = GameState.ENDED
            result["game_ended"] = True
            result["loser"] = user_id
            result["message"] = f"「{word}」で終了！<@{user_id}>さんの負けです。"
            return result
        
        # 単語を記録
        self.used_words.append(word)
        self.current_word = word
        self.game_history.append({
            "word": word,
            "user_id": user_id,
            "timestamp": datetime.datetime.now()
        })
        
        # 次のプレイヤーに移る
        self.current_player_index = (self.current_player_index + 1) % len(self.participants)
        next_player = self.get_current_player()
        
        result["success"] = True
        result["message"] = f"「{word}」→ 次は<@{next_player}>さんです！"
        
        return result
    
    def end_game(self) -> bool:
        """
        ゲームを強制終了する
        
        Returns:
            bool: 終了に成功した場合True
        """
        if self.state == GameState.IN_PROGRESS:
            self.state = GameState.ENDED
            return True
        return False
    
    def get_game_status(self) -> Dict:
        """
        現在のゲーム状況を取得する
        
        Returns:
            dict: ゲーム状況を含む辞書
        """
        status = {
            "state": self.state.value,
            "participants_count": len(self.participants),
            "current_word": self.current_word,
            "used_words_count": len(self.used_words),
            "current_player": self.get_current_player(),
            "start_time": self.start_time
        }
        
        if self.state == GameState.IN_PROGRESS:
            status["next_char"] = self.current_word[-1] if self.current_word else None
        
        return status
    
    def reset(self):
        """ゲームをリセットする"""
        self.__init__(self.game_type)  # ゲームタイプを保持してリセット
    
    def is_game_creator(self, user_id: int) -> bool:
        """
        指定されたユーザーがゲーム作成者かを確認する
        
        Args:
            user_id: 確認するUser ID
            
        Returns:
            bool: ゲーム作成者の場合True
        """
        return self.game_creator == user_id
    
    def is_association_game(self) -> bool:
        """
        連想しりとりかどうかを確認する
        
        Returns:
            bool: 連想しりとりの場合True
        """
        return self.game_type == GameType.ASSOCIATION
