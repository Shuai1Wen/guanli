#!/usr/bin/env python3
"""
PSC-Graph DAPT训练脚本

Domain-Adaptive Pre-Training (DAPT) 实现，符合CLAUDE.md要求：
- 基础模型：hfl/chinese-roberta-wwm-ext（哈工大中文RoBERTa）
- 训练任务：Masked Language Modeling (MLM)
- 训练轮数：3-5 epochs
- 学习率：5e-5
- Batch size：16-32（根据GPU显存调整）

目标：为通用预训练模型注入政策领域知识，提升下游任务性能

依赖：transformers, datasets, accelerate
"""

import torch
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

try:
    from transformers import (
        AutoTokenizer,
        AutoModelForMaskedLM,
        DataCollatorForLanguageModeling,
        Trainer,
        TrainingArguments,
        set_seed
    )
    from datasets import load_dataset
except ImportError:
    print("错误：transformers或datasets未安装")
    print("请运行: pip install transformers datasets accelerate")
    exit(1)


@dataclass
class DAPTConfig:
    """DAPT训练配置"""

    # 模型配置
    base_model: str = "hfl/chinese-roberta-wwm-ext"  # 哈工大中文RoBERTa
    tokenizer_max_length: int = 512

    # 数据配置
    corpus_path: str = "data/dapt_corpus.txt"
    train_test_split: float = 0.95  # 95%训练，5%验证

    # MLM配置
    mlm_probability: float = 0.15  # 15%的token被mask

    # 训练超参数
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 16
    per_device_eval_batch_size: int = 32
    learning_rate: float = 5e-5
    weight_decay: float = 0.01
    warmup_steps: int = 500
    gradient_accumulation_steps: int = 1  # 如果显存不足，增加此值

    # 输出配置
    output_dir: str = "results/dapt_checkpoints"
    final_model_dir: str = "results/dapt_model"
    logging_steps: int = 100
    eval_steps: int = 1000
    save_steps: int = 1000
    save_total_limit: int = 2  # 只保留最新的2个checkpoint

    # 其他配置
    seed: int = 42
    fp16: bool = True  # 使用混合精度训练（需要GPU）


class DAPTTrainer:
    """DAPT训练器"""

    def __init__(self, config: Optional[DAPTConfig] = None):
        """初始化训练器

        Args:
            config: 训练配置对象（可选，默认使用默认配置）
        """
        self.config = config if config is not None else DAPTConfig()

        # 设置随机种子
        set_seed(self.config.seed)

        # 检查语料文件
        if not Path(self.config.corpus_path).exists():
            raise FileNotFoundError(
                f"语料文件不存在: {self.config.corpus_path}\n"
                f"请先运行 prep_dapt_corpus.py 构建语料"
            )

        # 检查设备
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        if self.device == "cpu":
            print("警告：未检测到GPU，将使用CPU训练（速度较慢）")
            self.config.fp16 = False  # CPU不支持fp16

        print("=" * 80)
        print("PSC-Graph DAPT训练")
        print("=" * 80)
        print(f"\n配置信息：")
        print(f"  基础模型: {self.config.base_model}")
        print(f"  语料路径: {self.config.corpus_path}")
        print(f"  训练轮数: {self.config.num_train_epochs}")
        print(f"  学习率: {self.config.learning_rate}")
        print(f"  Batch size: {self.config.per_device_train_batch_size}")
        print(f"  设备: {self.device}")
        print(f"  混合精度: {self.config.fp16}")

    def load_tokenizer_and_model(self):
        """加载分词器和模型

        Returns:
            (tokenizer, model)
        """
        print("\n【步骤1】加载分词器和模型")
        print("-" * 80)

        # 加载分词器
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.base_model,
            model_max_length=self.config.tokenizer_max_length
        )
        print(f"  ✓ 分词器加载成功")
        print(f"    词表大小: {len(self.tokenizer):,}")
        print(f"    最大长度: {self.tokenizer.model_max_length}")

        # 加载模型
        self.model = AutoModelForMaskedLM.from_pretrained(self.config.base_model)
        print(f"  ✓ 模型加载成功")

        # 统计参数量
        total_params = sum(p.numel() for p in self.model.parameters())
        trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        print(f"    总参数量: {total_params:,}")
        print(f"    可训练参数: {trainable_params:,}")

        return self.tokenizer, self.model

    def load_and_preprocess_dataset(self):
        """加载和预处理数据集

        Returns:
            (train_dataset, eval_dataset)
        """
        print("\n【步骤2】加载和预处理数据集")
        print("-" * 80)

        # 加载文本文件
        print(f"  正在加载语料: {self.config.corpus_path}")
        dataset = load_dataset(
            'text',
            data_files=self.config.corpus_path,
            split='train'
        )
        print(f"  ✓ 语料加载成功")
        print(f"    样本数: {len(dataset):,}")

        # 切分训练集和验证集
        dataset = dataset.train_test_split(
            test_size=1 - self.config.train_test_split,
            seed=self.config.seed
        )
        train_dataset = dataset['train']
        eval_dataset = dataset['test']

        print(f"  ✓ 数据集切分完成")
        print(f"    训练集: {len(train_dataset):,} 样本")
        print(f"    验证集: {len(eval_dataset):,} 样本")

        # 分词预处理
        print(f"\n  正在进行分词预处理...")

        def tokenize_function(examples):
            """分词函数"""
            return self.tokenizer(
                examples['text'],
                truncation=True,
                max_length=self.config.tokenizer_max_length,
                padding=False,  # 动态padding由DataCollator处理
                return_special_tokens_mask=True
            )

        # 使用map进行批量处理
        tokenized_train = train_dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=train_dataset.column_names,
            desc="分词训练集"
        )

        tokenized_eval = eval_dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=eval_dataset.column_names,
            desc="分词验证集"
        )

        print(f"  ✓ 分词预处理完成")

        return tokenized_train, tokenized_eval

    def create_data_collator(self):
        """创建数据整理器

        DataCollator负责：
        1. 动态padding到batch内最大长度
        2. 随机mask 15%的token

        Returns:
            DataCollatorForLanguageModeling
        """
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=True,
            mlm_probability=self.config.mlm_probability
        )

        print(f"\n  ✓ 数据整理器创建成功")
        print(f"    MLM概率: {self.config.mlm_probability}")

        return data_collator

    def train(self):
        """执行DAPT训练

        完整流程：
        1. 加载模型和分词器
        2. 加载和预处理数据集
        3. 创建Trainer
        4. 训练
        5. 保存最终模型
        """
        # 步骤1：加载模型
        tokenizer, model = self.load_tokenizer_and_model()

        # 步骤2：加载数据集
        train_dataset, eval_dataset = self.load_and_preprocess_dataset()

        # 步骤3：创建数据整理器
        data_collator = self.create_data_collator()

        # 步骤4：配置训练参数
        print("\n【步骤3】配置训练参数")
        print("-" * 80)

        training_args = TrainingArguments(
            output_dir=self.config.output_dir,
            overwrite_output_dir=True,

            # 训练超参数
            num_train_epochs=self.config.num_train_epochs,
            per_device_train_batch_size=self.config.per_device_train_batch_size,
            per_device_eval_batch_size=self.config.per_device_eval_batch_size,
            learning_rate=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
            warmup_steps=self.config.warmup_steps,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,

            # 日志和保存
            logging_dir=f"{self.config.output_dir}/logs",
            logging_steps=self.config.logging_steps,
            eval_strategy="steps",
            eval_steps=self.config.eval_steps,
            save_steps=self.config.save_steps,
            save_total_limit=self.config.save_total_limit,

            # 优化
            fp16=self.config.fp16,

            # 其他
            seed=self.config.seed,
            report_to="none",  # 不使用wandb等外部日志
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
        )

        print(f"  ✓ 训练参数配置完成")
        print(f"    输出目录: {self.config.output_dir}")

        # 步骤5：创建Trainer
        print("\n【步骤4】创建Trainer")
        print("-" * 80)

        trainer = Trainer(
            model=model,
            args=training_args,
            data_collator=data_collator,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
        )

        print(f"  ✓ Trainer创建成功")

        # 步骤6：训练
        print("\n【步骤5】开始训练")
        print("-" * 80)
        print()

        try:
            train_result = trainer.train()

            print("\n" + "-" * 80)
            print(f"  ✓ 训练完成")
            print(f"    最终训练损失: {train_result.training_loss:.4f}")
            print(f"    训练时长: {train_result.metrics['train_runtime']:.2f}秒")

        except KeyboardInterrupt:
            print("\n\n⚠️  训练被用户中断")
            print("  部分训练的模型已保存在checkpoint中")
            return

        # 步骤7：评估
        print("\n【步骤6】评估模型")
        print("-" * 80)

        eval_result = trainer.evaluate()
        print(f"  ✓ 评估完成")
        print(f"    验证集损失: {eval_result['eval_loss']:.4f}")
        print(f"    验证集困惑度: {torch.exp(torch.tensor(eval_result['eval_loss'])):.4f}")

        # 步骤8：保存最终模型
        print("\n【步骤7】保存最终模型")
        print("-" * 80)

        Path(self.config.final_model_dir).mkdir(parents=True, exist_ok=True)

        model.save_pretrained(self.config.final_model_dir)
        tokenizer.save_pretrained(self.config.final_model_dir)

        print(f"  ✓ 模型已保存到: {self.config.final_model_dir}")

        # 最终报告
        print("\n" + "=" * 80)
        print("DAPT训练完成 ✓")
        print("=" * 80)
        print(f"\n模型性能：")
        print(f"  训练损失: {train_result.training_loss:.4f}")
        print(f"  验证损失: {eval_result['eval_loss']:.4f}")
        print(f"  困惑度: {torch.exp(torch.tensor(eval_result['eval_loss'])):.4f}")
        print(f"\n下一步：")
        print(f"  1. 使用DAPT模型进行TAPT训练 (run_tapt.py)")
        print(f"  2. 或直接用于下游任务微调")


def main():
    """主函数"""
    # 使用默认配置
    config = DAPTConfig()

    # 如果显存不足（<16GB），调整以下参数：
    # config.per_device_train_batch_size = 8
    # config.gradient_accumulation_steps = 2  # 有效batch size = 8*2 = 16

    # 创建训练器
    trainer = DAPTTrainer(config)

    # 开始训练
    trainer.train()


if __name__ == "__main__":
    main()
