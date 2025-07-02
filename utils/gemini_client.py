"""
Client for communication with Gemini API
"""
import os
import asyncio
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class GeminiClient:
    """Gemini API client class"""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set. Please check the .env file.")
        
        # Configure Gemini API
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    
    async def validate_word(self, word: str) -> tuple[bool, str]:
        """
        Validate if a word exists using Gemini API
        
        Args:
            word: Word to validate
            
        Returns:
            tuple: (validation result(bool), reason/explanation(str))
        """
        try:
            prompt = f"""
以下の単語について、日本語の一般的な名詞として実在するかを判定してください。
固有名詞、人名、地名、ブランド名、略語、造語、俗語は除外してください。

単語: {word}

以下の形式で回答してください：
判定: [OK/NG]
理由: [判定の理由を簡潔に]

例：
判定: OK
理由: 一般的な動物の名前として辞書に記載されています。

判定: NG
理由: 固有名詞のため、しりとりでは使用できません。
"""
            
            # 非同期でAPIを呼び出し
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            response_text = response.text.strip()
            
            # レスポンスを解析
            is_valid = False
            reason = "APIからの応答を解析できませんでした。"
            
            lines = response_text.split('\n')
            for line in lines:
                if line.startswith('判定:'):
                    judgment = line.replace('判定:', '').strip()
                    is_valid = judgment == 'OK'
                elif line.startswith('理由:'):
                    reason = line.replace('理由:', '').strip()
            
            return is_valid, reason
            
        except Exception as e:
            # APIエラーの場合はデフォルトでOKとする（安全側に倒す）
            return True, f"API検証中にエラーが発生しました: {str(e)}"
    
    async def get_word_suggestion(self, last_char: str, used_words: list) -> Optional[str]:
        """
        指定された文字で始まる単語の提案を取得する
        
        Args:
            last_char: 単語の最初の文字
            used_words: 使用済みの単語リスト
            
        Returns:
            str: 提案する単語、失敗した場合はNone
        """
        try:
            used_words_str = ', '.join(used_words[-10:])  # 最新10個の単語のみ表示
            
            prompt = f"""
しりとりゲームで、「{last_char}」で始まる日本語の一般的な名詞を1つ提案してください。
以下の単語は既に使用されているので避けてください：{used_words_str}

条件：
- 一般的な名詞のみ（固有名詞、人名、地名は除く）
- 「ん」で終わらない単語
- ひらがなまたはカタカナで表記
- 単語のみを回答（説明不要）

回答例：
りんご
"""
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            suggested_word = response.text.strip()
            
            # 提案された単語が条件を満たすかチェック
            if (suggested_word and 
                suggested_word[0].lower() == last_char.lower() and
                not suggested_word.endswith('ん') and
                suggested_word not in used_words):
                return suggested_word
            
            return None
            
        except Exception as e:
            print(f"単語提案中にエラーが発生しました: {e}")
            return None
    
    async def explain_word(self, word: str) -> str:
        """
        単語の意味を説明する
        
        Args:
            word: 説明する単語
            
        Returns:
            str: 単語の説明
        """
        try:
            prompt = f"""
「{word}」という単語の意味を、小学生にもわかりやすく簡潔に説明してください。
1-2文で回答してください。

例：
りんご: 赤や青い色をした甘い果物です。
"""
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            return response.text.strip()
            
        except Exception as e:
            return f"説明の取得に失敗しました: {str(e)}"
    
    async def validate_association(self, previous_word: str, current_word: str) -> dict:
        """
        連想しりとりの連想が適切かを検証する
        
        Args:
            previous_word: 前の単語
            current_word: 現在の単語
            
        Returns:
            dict: {"valid": bool, "reason": str}
        """
        try:
            prompt = f"""
連想しりとりで「{previous_word}」から「{current_word}」への連想は適切ですか？

連想の基準：
- 意味的な関連性がある
- 色彩、形状、機能、カテゴリ、イメージなどで関連している
- 日常的に連想可能な範囲である
- あまりにも無理やりな関連付けではない

適切な例：
- りんご → 赤 (色の関連)
- 海 → 青 (色・イメージの関連)
- 犬 → 動物 (カテゴリの関連)
- 車 → 速い (機能・特徴の関連)

「YES」または「NO: [理由]」で回答してください。
理由は簡潔に書いてください。
"""
            
            response = await self.client.generate_content_async(prompt)
            result_text = response.text.strip()
            
            if result_text.startswith("YES"):
                return {"valid": True, "reason": "適切な連想です"}
            elif result_text.startswith("NO"):
                reason = result_text.replace("NO:", "").strip()
                if not reason:
                    reason = "連想が不適切です"
                return {"valid": False, "reason": reason}
            else:
                # 予期しない応答の場合はエラーとして扱う
                return {"valid": False, "reason": "連想の適切性を判定できませんでした"}
                
        except Exception as e:
            # エラーの場合は寛容に判定（ゲーム進行を優先）
            return {"valid": True, "reason": f"判定エラーのため通過: {str(e)}"}


# グローバルインスタンス
_gemini_client = None


def get_gemini_client() -> GeminiClient:
    """
    Gemini クライアントのシングルトンインスタンスを取得する
    
    Returns:
        GeminiClient: クライアントインスタンス
    """
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
