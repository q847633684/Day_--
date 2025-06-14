import xml.etree.ElementTree as ET
import csv
import os
from pathlib import Path
import logging

def inplace_update_xml_etree(xml_path, csv_dict):
    """
    只替换已有key内容，不新增，顺序保留，注释丢失。
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        changed = False
        for elem in root:
            if elem.tag in csv_dict:
                elem.text = csv_dict[elem.tag]
                changed = True
        if changed:
            tree.write(xml_path, encoding="utf-8", xml_declaration=True)
            logging.info(f"更新 XML 文件: {xml_path}")
    except ET.ParseError as e:
        logging.error(f"XML 解析失败: {xml_path}，错误: {e}")
    except FileNotFoundError as e:
        logging.error(f"文件未找到: {xml_path}，错误: {e}")

def inplace_update_all_xml(csv_path, mod_root_dir):
    """
    批量遍历 DefInjected 和 Keyed 下所有 xml 文件。
    """
    if not os.path.exists(csv_path):
        logging.error(f"CSV 文件不存在: {csv_path}")
        return
    csv_dict = {}
    try:
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row["key"]
                if "/" in key and "." in key:
                    key = key.split("/")[-1]
                value = row.get("translated") or row["text"]
                csv_dict[key] = value
    except FileNotFoundError as e:
        logging.error(f"CSV 文件未找到: {csv_path}，错误: {e}")
        return
    except csv.Error as e:
        logging.error(f"CSV 解析失败: {csv_path}，错误: {e}")
        return
    def_injected_dir = os.path.join(mod_root_dir, "Languages", "ChineseSimplified", "DefInjected")
    if not os.path.exists(def_injected_dir):
        def_injected_dir = os.path.join(mod_root_dir, "Languages", "ChineseSimplified", "DefInjured")
        if not os.path.exists(def_injected_dir):
            logging.error(f"未找到 DefInjected 或 DefInjured 目录: {os.path.join(mod_root_dir, 'Languages', 'ChineseSimplified')}")
            return
    for xml_file in Path(def_injected_dir).rglob("*.xml"):
        inplace_update_xml_etree(str(xml_file), csv_dict)
    keyed_dir = os.path.join(mod_root_dir, "Languages", "ChineseSimplified", "Keyed")
    for xml_file in Path(keyed_dir).rglob("*.xml"):
        inplace_update_xml_etree(str(xml_file), csv_dict)