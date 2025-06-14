import csv
import logging
import os
import re
import time
from typing import List, Dict
from pathlib import Path

try:
    from aliyunsdkcore.client import AcsClient
    from aliyunsdkalimt.request.v20181012 import TranslateGeneralRequest
except ImportError:
    logging.warning("阿里云 SDK 未安装，机器翻译功能不可用。请运行：pip install aliyun-python-sdk-core aliyun-python-sdk-alimt")
    AcsClient = None
    TranslateGeneralRequest = None

def translate_text(text: str, access_key_id: str, access_secret: str) -> str:
    """使用阿里云翻译 API 翻译文本，保留 [xxx] 占位符"""
    if AcsClient is None or TranslateGeneralRequest is None:
        raise RuntimeError("阿里云 SDK 未安装，无法进行机器翻译")
    
    # 检查是否只包含占位符
    if re.fullmatch(r'(\s*\[[^\]]+\]\s*)+', text):
        return text
    
    try:
        # 分割文本，保留占位符
        parts = re.split(r'(\[[^\]]+\])', text)
        translated_parts = []
        
        for part in parts:
            if re.fullmatch(r'\[[^\]]+\]', part):
                # 这是占位符，直接保留
                translated_parts.append(part)
            elif part.strip():
                # 这是需要翻译的文本
                client = AcsClient(access_key_id, access_secret, "cn-hangzhou")
                request = TranslateGeneralRequest()
                request.set_accept_format("json")
                request.set_SourceLanguage("en")
                request.set_TargetLanguage("zh")
                request.set_SourceText(part)
                response = client.do_action_with_exception(request)
                import json
                result = json.loads(response)
                translated_text = result.get("Data", {}).get("Translated", part)
                translated_parts.append(translated_text)
            else:
                # 空白部分
                translated_parts.append(part)
        
        return ''.join(translated_parts)
        
    except Exception as e:
        logging.error(f"翻译失败: {text}, 错误: {e}")
        return text

def translate_csv(
    input_path: str,
    output_path: str,
    access_key_id: str,
    access_secret: str,
    region_id: str = "cn-hangzhou",
    sleep_sec: float = 0.5
) -> None:
    """翻译 CSV 文件中的文本，支持速率控制"""
    logging.info(f"翻译 CSV: input={input_path}, output={output_path}, region_id={region_id}, sleep_sec={sleep_sec}")
    
    if not os.path.exists(input_path):
        logging.error(f"输入 CSV 文件不存在: {input_path}")
        return
    
    rows: List[Dict[str, str]] = []
    try:
        with open(input_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if "text" not in reader.fieldnames:
                logging.error(f"CSV 文件缺少 'text' 列: {input_path}")
                return
            
            for line_num, row in enumerate(reader, 2):  # 从第2行开始计数
                text = row["text"].strip()
                if not text:
                    row["translated"] = ""
                elif re.fullmatch(r'(\s*\[[^\]]+\]\s*)+', text):
                    # 只包含占位符，不翻译
                    row["translated"] = text
                else:
                    translated = translate_text(text, access_key_id, access_secret)
                    row["translated"] = translated
                    if not translated or translated.strip() == "":
                        logging.warning(f"第{line_num}行翻译失败。原文：{text}")
                    else:
                        logging.debug(f"第{line_num}行翻译完成：{text} => {translated}")
                
                rows.append(row)
                time.sleep(sleep_sec)  # 速率控制
                
    except csv.Error as e:
        logging.error(f"CSV 解析失败: {input_path}, 错误: {e}")
        return
    except OSError as e:
        logging.error(f"无法读取 CSV: {input_path}, 错误: {e}")
        return
    output_dir = os.path.dirname(output_path) or "."
    if not os.access(output_dir, os.W_OK):
        logging.error(f"输出目录 {output_dir} 无写入权限")
        return
    try:
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            fieldnames = rows[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        logging.info(f"翻译完成，保存到: {output_path}")
        print(f"翻译完成，保存到: {output_path}")
    except csv.Error as e:
        logging.error(f"CSV 写入失败: {output_path}, 错误: {e}")
    except OSError as e:
        logging.error(f"无法写入 CSV: {output_path}, 错误: {e}")