#!/usr/bin/env Rscript
# -*- coding: utf-8 -*-
#
# DID因果推断估计脚本
#
# 功能：
# 1. CS-ATT估计（Callaway & Sant'Anna）
# 2. Sun-Abraham估计
# 3. BJS Imputation估计（Borusyak-Jaravel-Spiess）
# 4. 预趋势检验
# 5. 稳健性检验
# 6. 事件研究图可视化
#
# 输入：
# - data/panel_for_did.csv：标准DID面板数据
#
# 输出：
# - results/did_csatt_event.csv：CS-ATT事件研究结果
# - results/did_csatt_overall.csv：CS-ATT总体ATT
# - results/did_sunab_event.csv：Sun-Abraham事件研究结果
# - results/did_bjs_overall.csv：BJS总体ATT
# - results/did_pretrend_test.csv：预趋势检验结果
# - results/did_event_study.pdf：事件研究图

# 检查并安装必需的R包
packages <- c("did", "fixest", "didimputation", "dplyr", "ggplot2", "data.table")

for (pkg in packages) {
  if (!require(pkg, character.only = TRUE, quietly = TRUE)) {
    message(sprintf("安装R包: %s", pkg))
    install.packages(pkg, repos = "https://cloud.r-project.org/", quiet = TRUE)
    library(pkg, character.only = TRUE)
  }
}

# 加载必需的包
suppressPackageStartupMessages({
  library(did)
  library(fixest)
  library(didimputation)
  library(dplyr)
  library(ggplot2)
  library(data.table)
})

#' 加载面板数据
#'
#' @param panel_path 面板数据CSV文件路径
#' @return 面板数据data.frame
load_panel_data <- function(panel_path) {
  cat("\n=== 加载面板数据 ===\n")

  if (!file.exists(panel_path)) {
    stop(sprintf("面板数据文件不存在: %s", panel_path))
  }

  panel <- fread(panel_path, encoding = "UTF-8")
  panel <- as.data.frame(panel)

  cat(sprintf("✓ 加载数据：%d行 × %d列\n", nrow(panel), ncol(panel)))
  cat(sprintf("  时间范围：%d-%d\n", min(panel$time), max(panel$time)))
  cat(sprintf("  地区数量：%d\n", length(unique(panel$id))))

  # 检查必需字段
  required_cols <- c("id", "time", "y", "g", "treat")
  missing <- setdiff(required_cols, colnames(panel))
  if (length(missing) > 0) {
    stop(sprintf("缺少必需列: %s", paste(missing, collapse = ", ")))
  }

  # 转换类型
  panel$id <- as.character(panel$id)
  panel$time <- as.integer(panel$time)
  panel$g <- as.integer(panel$g)
  panel$treat <- as.integer(panel$treat)

  return(panel)
}

#' CS-ATT估计（Callaway & Sant'Anna）
#'
#' @param panel 面板数据
#' @param yname 结果变量名
#' @param gname 首次处理时点变量名
#' @param idname 个体ID变量名
#' @param tname 时间变量名
#' @param control_group 对照组类型（"nevertreated"或"notyettreated"）
#' @return did包的ATT估计结果
estimate_csatt <- function(
  panel,
  yname = "y",
  gname = "g",
  idname = "id",
  tname = "time",
  control_group = "nevertreated"
) {
  cat("\n=== CS-ATT估计（Callaway & Sant'Anna）===\n")

  # 估计组-时点ATT
  att_gt <- att_gt(
    yname = yname,
    gname = gname,
    idname = idname,
    tname = tname,
    data = panel,
    control_group = control_group,
    base_period = "universal",
    clustervars = idname,
    est_method = "dr",  # 双重稳健估计
    print_details = FALSE
  )

  cat("✓ 组-时点ATT估计完成\n")

  # 汇总：事件研究（event study）
  es <- aggte(att_gt, type = "dynamic", na.rm = TRUE)
  cat("✓ 事件研究汇总完成\n")

  # 汇总：总体ATT
  overall <- aggte(att_gt, type = "simple", na.rm = TRUE)
  cat(sprintf("✓ 总体ATT: %.4f (SE: %.4f)\n", overall$overall.att, overall$overall.se))

  # 返回结果列表
  return(list(
    att_gt = att_gt,
    event_study = es,
    overall = overall
  ))
}

#' Sun-Abraham估计
#'
#' @param panel 面板数据
#' @param yname 结果变量名
#' @param controls 控制变量向量
#' @return fixest估计结果
estimate_sunab <- function(panel, yname = "y", controls = c()) {
  cat("\n=== Sun-Abraham估计 ===\n")

  # 构建公式
  control_formula <- if (length(controls) > 0) {
    paste("+", paste(controls, collapse = " + "))
  } else {
    ""
  }

  formula_str <- sprintf(
    "%s ~ sunab(g, time) %s | id + time",
    yname,
    control_formula
  )

  cat(sprintf("公式: %s\n", formula_str))

  # 估计
  est <- feols(
    as.formula(formula_str),
    data = panel,
    cluster = ~id
  )

  cat("✓ Sun-Abraham估计完成\n")

  # 提取事件研究系数
  coef_names <- names(coef(est))
  event_coefs <- grep("time::", coef_names, value = TRUE)

  if (length(event_coefs) > 0) {
    cat(sprintf("✓ 提取到%d个事件研究系数\n", length(event_coefs)))
  }

  return(est)
}

#' BJS Imputation估计（Borusyak-Jaravel-Spiess）
#'
#' @param panel 面板数据
#' @param yname 结果变量名
#' @return didimputation估计结果
estimate_bjs <- function(panel, yname = "y") {
  cat("\n=== BJS Imputation估计 ===\n")

  # 使用did_imputation函数
  est <- did_imputation(
    data = panel,
    yname = yname,
    gname = "g",
    tname = "time",
    idname = "id",
    first_stage = ~ 0,  # 无额外协变量
    horizon = TRUE,  # 估计动态效应
    pretrends = TRUE  # 进行预趋势检验
  )

  cat("✓ BJS估计完成\n")

  # 计算总体ATT（事后处理期平均）
  post_treat <- est[est$term >= 0, ]
  if (nrow(post_treat) > 0) {
    overall_att <- mean(post_treat$estimate, na.rm = TRUE)
    cat(sprintf("✓ 总体ATT（处理后平均）: %.4f\n", overall_att))
  }

  return(est)
}

#' 预趋势检验
#'
#' @param cs_result CS-ATT估计结果
#' @param sunab_result Sun-Abraham估计结果
#' @return 预趋势检验结果data.frame
pretrend_test <- function(cs_result, sunab_result) {
  cat("\n=== 预趋势检验 ===\n")

  results <- list()

  # CS-ATT预趋势检验
  es <- cs_result$event_study
  pre_periods <- es$egt < 0

  if (sum(pre_periods) > 0) {
    pre_att <- es$att.egt[pre_periods]
    pre_se <- es$se.egt[pre_periods]

    # 联合F检验（简化版：检查是否所有预期系数不显著）
    pre_significant <- abs(pre_att / pre_se) > 1.96

    cs_pass <- !any(pre_significant, na.rm = TRUE)

    results$cs_att <- data.frame(
      method = "CS-ATT",
      pretrend_pass = cs_pass,
      pre_periods = sum(pre_periods),
      significant_pre = sum(pre_significant, na.rm = TRUE)
    )

    cat(sprintf("CS-ATT预趋势检验: %s\n", ifelse(cs_pass, "通过✓", "未通过✗")))
    cat(sprintf("  预处理期数: %d\n", sum(pre_periods)))
    cat(sprintf("  显著预期系数数: %d\n", sum(pre_significant, na.rm = TRUE)))
  }

  # Sun-Abraham预趋势（从fixest提取）
  # 这里简化处理，实际应从估计结果中提取预期系数
  results$sunab <- data.frame(
    method = "Sun-Abraham",
    pretrend_pass = NA,  # 需要手动检查fixest输出
    pre_periods = NA,
    significant_pre = NA
  )

  result_df <- do.call(rbind, results)

  return(result_df)
}

#' 绘制事件研究图
#'
#' @param cs_result CS-ATT估计结果
#' @param output_path 输出PDF路径
plot_event_study <- function(cs_result, output_path) {
  cat("\n=== 绘制事件研究图 ===\n")

  es <- cs_result$event_study

  # 准备绘图数据
  plot_data <- data.frame(
    event_time = es$egt,
    att = es$att.egt,
    se = es$se.egt,
    ci_lower = es$att.egt - 1.96 * es$se.egt,
    ci_upper = es$att.egt + 1.96 * es$se.egt
  )

  # 移除NA
  plot_data <- plot_data[complete.cases(plot_data), ]

  # 绘图
  p <- ggplot(plot_data, aes(x = event_time, y = att)) +
    geom_line(color = "blue", size = 1) +
    geom_point(color = "blue", size = 2) +
    geom_ribbon(aes(ymin = ci_lower, ymax = ci_upper), alpha = 0.2, fill = "blue") +
    geom_hline(yintercept = 0, linetype = "dashed", color = "red") +
    geom_vline(xintercept = -0.5, linetype = "dotted", color = "gray50") +
    labs(
      title = "事件研究图（CS-ATT）",
      subtitle = "政策效应的动态分析",
      x = "相对于处理的时间（年）",
      y = "平均处理效应（ATT）"
    ) +
    theme_minimal() +
    theme(
      plot.title = element_text(hjust = 0.5, size = 14, face = "bold"),
      plot.subtitle = element_text(hjust = 0.5, size = 10)
    )

  # 保存
  ggsave(output_path, plot = p, width = 10, height = 6)
  cat(sprintf("✓ 事件研究图已保存: %s\n", output_path))
}

#' 保存估计结果
#'
#' @param cs_result CS-ATT估计结果
#' @param sunab_result Sun-Abraham估计结果
#' @param bjs_result BJS估计结果
#' @param pretrend_result 预趋势检验结果
#' @param output_dir 输出目录
save_results <- function(cs_result, sunab_result, bjs_result, pretrend_result, output_dir) {
  cat("\n=== 保存估计结果 ===\n")

  # 创建输出目录
  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE)
  }

  # 1. CS-ATT事件研究结果
  es <- cs_result$event_study
  cs_event <- data.frame(
    event_time = es$egt,
    att = es$att.egt,
    se = es$se.egt,
    ci_lower = es$att.egt - 1.96 * es$se.egt,
    ci_upper = es$att.egt + 1.96 * es$se.egt
  )
  cs_event_path <- file.path(output_dir, "did_csatt_event.csv")
  write.csv(cs_event, cs_event_path, row.names = FALSE, fileEncoding = "UTF-8")
  cat(sprintf("✓ CS-ATT事件研究: %s\n", cs_event_path))

  # 2. CS-ATT总体ATT
  overall <- cs_result$overall
  cs_overall <- data.frame(
    method = "CS-ATT",
    overall_att = overall$overall.att,
    overall_se = overall$overall.se,
    ci_lower = overall$overall.att - 1.96 * overall$overall.se,
    ci_upper = overall$overall.att + 1.96 * overall$overall.se
  )
  cs_overall_path <- file.path(output_dir, "did_csatt_overall.csv")
  write.csv(cs_overall, cs_overall_path, row.names = FALSE, fileEncoding = "UTF-8")
  cat(sprintf("✓ CS-ATT总体ATT: %s\n", cs_overall_path))

  # 3. Sun-Abraham事件研究（从fixest提取）
  # 这里简化，实际应从sunab_result中提取系数
  sunab_event_path <- file.path(output_dir, "did_sunab_event.csv")
  # 占位：需要手动从fixest结果提取
  sunab_coef <- summary(sunab_result)$coeftable
  write.csv(sunab_coef, sunab_event_path, fileEncoding = "UTF-8")
  cat(sprintf("✓ Sun-Abraham结果: %s\n", sunab_event_path))

  # 4. BJS总体ATT
  if (!is.null(bjs_result)) {
    post_treat <- bjs_result[bjs_result$term >= 0, ]
    bjs_overall <- data.frame(
      method = "BJS",
      overall_att = mean(post_treat$estimate, na.rm = TRUE),
      # BJS的标准误需要从估计中提取
      note = "处理后期间平均ATT"
    )
    bjs_overall_path <- file.path(output_dir, "did_bjs_overall.csv")
    write.csv(bjs_overall, bjs_overall_path, row.names = FALSE, fileEncoding = "UTF-8")
    cat(sprintf("✓ BJS总体ATT: %s\n", bjs_overall_path))

    # 也保存完整BJS结果
    bjs_full_path <- file.path(output_dir, "did_bjs_full.csv")
    write.csv(bjs_result, bjs_full_path, row.names = FALSE, fileEncoding = "UTF-8")
  }

  # 5. 预趋势检验结果
  pretrend_path <- file.path(output_dir, "did_pretrend_test.csv")
  write.csv(pretrend_result, pretrend_path, row.names = FALSE, fileEncoding = "UTF-8")
  cat(sprintf("✓ 预趋势检验: %s\n", pretrend_path))
}

#' 主函数
#'
#' @param panel_path 面板数据路径（可选，从命令行参数获取）
#' @param output_dir 输出目录路径（可选，从命令行参数获取）
#' @param estimators 估计器列表（可选，从命令行参数获取，逗号分隔）
main <- function(panel_path = NULL, output_dir = NULL, estimators = NULL) {
  cat("=" * 60, "\n")
  cat("DID因果推断估计\n")
  cat("=" * 60, "\n")

  # 设置默认路径
  if (is.null(panel_path) || is.null(output_dir)) {
    script_dir <- dirname(sys.frame(1)$ofile)
    if (is.null(script_dir) || script_dir == "") {
      script_dir <- getwd()
    }
    project_root <- dirname(script_dir)

    if (is.null(panel_path)) {
      panel_path <- file.path(project_root, "data", "panel_for_did.csv")
    }
    if (is.null(output_dir)) {
      output_dir <- file.path(project_root, "results")
    }
  }

  # 解析估计器列表
  if (is.null(estimators)) {
    estimators <- c("csatt", "sunab", "bjs")
  } else if (is.character(estimators) && length(estimators) == 1) {
    # 如果是逗号分隔的字符串，拆分
    estimators <- strsplit(estimators, ",")[[1]]
    estimators <- trimws(estimators)
  }

  cat(sprintf("面板数据: %s\n", panel_path))
  cat(sprintf("输出目录: %s\n", output_dir))
  cat(sprintf("估计器: %s\n", paste(estimators, collapse = ", ")))
  cat("\n")

  # 1. 加载数据
  panel <- load_panel_data(panel_path)

  # 初始化结果
  cs_result <- NULL
  sunab_result <- NULL
  bjs_result <- NULL

  # 2. CS-ATT估计
  if ("csatt" %in% estimators) {
    cat("\n--- 运行CS-ATT估计 ---\n")
    cs_result <- estimate_csatt(panel)
  }

  # 3. Sun-Abraham估计
  if ("sunab" %in% estimators) {
    cat("\n--- 运行Sun-Abraham估计 ---\n")
    sunab_result <- estimate_sunab(panel)
  }

  # 4. BJS估计
  if ("bjs" %in% estimators) {
    cat("\n--- 运行BJS估计 ---\n")
    bjs_result <- tryCatch(
      {
        estimate_bjs(panel)
      },
      error = function(e) {
        cat(sprintf("警告：BJS估计失败: %s\n", e$message))
        return(NULL)
      }
    )
  }

  # 5. 预趋势检验（如果有CS或Sun-Abraham结果）
  if (!is.null(cs_result) || !is.null(sunab_result)) {
    cat("\n--- 预趋势检验 ---\n")
    pretrend_result <- pretrend_test(cs_result, sunab_result)
  } else {
    pretrend_result <- data.frame(
      estimator = character(),
      test_type = character(),
      result = character(),
      stringsAsFactors = FALSE
    )
  }

  # 6. 绘制事件研究图
  if (!is.null(cs_result)) {
    cat("\n--- 绘制事件研究图 ---\n")
    event_plot_path <- file.path(output_dir, "did_event_study.pdf")
    plot_event_study(cs_result, event_plot_path)
  }

  # 7. 保存结果
  cat("\n--- 保存结果 ---\n")
  save_results(cs_result, sunab_result, bjs_result, pretrend_result, output_dir)

  cat("\n", "=" * 60, "\n")
  cat("DID估计完成\n")
  cat("=" * 60, "\n")

  # 输出会话信息（用于复现）
  cat("\nR会话信息:\n")
  print(sessionInfo())
}

# 执行主函数（从命令行参数获取）
if (!interactive()) {
  args <- commandArgs(trailingOnly = TRUE)

  if (length(args) >= 2) {
    # 从命令行参数获取
    panel_path <- args[1]
    output_dir <- args[2]
    estimators <- if (length(args) >= 3) args[3] else NULL

    main(panel_path, output_dir, estimators)
  } else {
    # 使用默认路径
    main()
  }
}
