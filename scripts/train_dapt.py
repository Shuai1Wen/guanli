#!/usr/bin/env python3
"""
PSC-Graph DAPT/TAPT 预训练脚本

实现域适应预训练 (Domain-Adaptive Pre-training) 和任务自适应预训练 (Task-Adaptive Pre-training)
符合CLAUDE.md强制规范：
- 基础模型: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
- 训练方式: Masked Language Modeling (MLM)
- 数据源: 政策文档全量文本 (DAPT) 或 任务相关文本 (TAPT)

依赖: transformers, datasets, torch
"""

import sys
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

import torch
from transformers import (
    AutoModelForMaskedLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
    HfArgumentParser
)
from datasets import load_dataset, Dataset

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 初始化日志
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

@dataclass
class ModelArguments:
    """模型参数"""
    model_name_or_path: str = field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        metadata={"help": "基础模型名称或路径"}
    )
    tokenizer_name: Optional[str] = field(
        default=None,
        metadata={"help": "分词器名称 (默认同模型)"}
    )

@dataclass
class DataArguments:
    """数据参数"""
    train_file: Optional[str] = field(
        default=None, 
        metadata={"help": "训练数据文件路径 (txt/json/csv)"}
    )
    validation_file: Optional[str] = field(
        default=None,
        metadata={"help": "验证数据文件路径"}
    )
    max_seq_length: int = field(
        default=512,
        metadata={"help": "最大序列长度"}
    )
    mlm_probability: float = field(
        default=0.15,
        metadata={"help": "MLM掩码比例"}
    )
    overwrite_cache: bool = field(
        default=False,
        metadata={"help": "是否覆盖缓存"}
    )

def main():
    """主函数"""
    # 解析参数
    parser = HfArgumentParser((ModelArguments, DataArguments, TrainingArguments))
    if len(sys.argv) == 2 and sys.argv[1].endswith(".json"):
        # 支持从json文件加载参数
        model_args, data_args, training_args = parser.parse_json_file(json_file=os.path.abspath(sys.argv[1]))
    else:
        # 默认参数（如果未提供命令行参数）
        # 为了演示，我们设置一些默认值，实际使用时应通过命令行传入
        if len(sys.argv) == 1:
            sys.argv.extend([
                "--output_dir", "results/dapt_model",
                "--num_train_epochs", "3",
                "--per_device_train_batch_size", "8",
                "--save_steps", "1000",
                "--logging_steps", "100",
                "--do_train",
            ])
        model_args, data_args, training_args = parser.parse_args_into_dataclasses()

    logger.info(f"模型参数: {model_args}")
    logger.info(f"数据参数: {data_args}")
    logger.info(f"训练参数: {training_args}")

    # 1. 加载模型和分词器
    logger.info("正在加载模型和分词器...")
    tokenizer = AutoTokenizer.from_pretrained(
        model_args.tokenizer_name or model_args.model_name_or_path
    )
    model = AutoModelForMaskedLM.from_pretrained(
        model_args.model_name_or_path
    )

    # 2. 准备数据
    logger.info("正在准备数据...")
    if data_args.train_file:
        # 从文件加载
        extension = data_args.train_file.split(".")[-1]
        raw_datasets = load_dataset(extension, data_files={"train": data_args.train_file})
    else:
        # 演示模式：使用corpus/raw下的所有json文件中的content_text
        # 这里为了演示，我们创建一个简单的内存数据集
        logger.warning("未指定训练文件，将扫描 corpus/raw 目录下的数据...")
        corpus_dir = PROJECT_ROOT / "corpus/raw"
        texts = []
        for json_file in corpus_dir.rglob("*.json"):
            try:
                import json
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "content_text" in data:
                        texts.append(data["content_text"])
            except Exception as e:
                logger.warning(f"读取文件失败 {json_file}: {e}")
        
        if not texts:
            logger.warning("未找到任何语料，将使用示例文本进行演示")
            texts = [
                "科技政策是推动创新的重要手段。",
                "本省将加大对高新技术企业的支持力度。",
                "根据相关规定，申请该项目的企业需要满足以下条件...",
                "加强基础研究，提升原始创新能力。"
            ] * 10 # 重复以模拟数据
            
        raw_datasets = Dataset.from_dict({"text": texts})
        # 包装成DatasetDict以便统一处理
        from datasets import DatasetDict
        raw_datasets = DatasetDict({"train": raw_datasets})

    # 3. 预处理数据
    column_names = raw_datasets["train"].column_names
    text_column_name = "text" if "text" in column_names else column_names[0]

    def tokenize_function(examples):
        return tokenizer(
            examples[text_column_name],
            padding="max_length",
            truncation=True,
            max_length=data_args.max_seq_length,
            return_special_tokens_mask=True,
        )

    tokenized_datasets = raw_datasets.map(
        tokenize_function,
        batched=True,
        num_proc=4,
        remove_columns=column_names,
        load_from_cache_file=not data_args.overwrite_cache,
    )

    # 4. 数据整理器 (MLM)
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=True,
        mlm_probability=data_args.mlm_probability
    )

    # 5. 初始化Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets["train"],
        tokenizer=tokenizer,
        data_collator=data_collator,
    )

    # 6. 开始训练
    logger.info("开始DAPT/TAPT训练...")
    train_result = trainer.train()
    trainer.save_model()  # 保存最终模型
    
    metrics = train_result.metrics
    trainer.log_metrics("train", metrics)
    trainer.save_metrics("train", metrics)
    trainer.save_state()

    logger.info(f"训练完成，模型已保存到: {training_args.output_dir}")

if __name__ == "__main__":
    main()
