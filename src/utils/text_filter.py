import re

class TextFilter:
    DEFAULT_INVALID_WORD = ['', '百度APP内打开', '大家还在搜']
    @staticmethod
    def filter_useless(text, filter=DEFAULT_INVALID_WORD, replacement=""):
        """
        使用正则表达式过滤无用文本
    
        Args:
            text (str): 原始文本
            filter (list, optional): 需要过滤的文本列表.
            replacement (str, optional): 用于替换过滤文本的字符串.
        Returns:
            str: 过滤后的文本。
        """
        if not text or not filter:
            return text
        pattern = "|".join(map(re.escape, filter))
        text = re.sub(pattern, replacement, text)
        return re.sub(r'\n{3,}', '\n\n', text).strip()