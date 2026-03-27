---
name: habit-reminder
description: 创建习惯养成提醒系统，使用多维度轰炸策略帮助用户建立新习惯。触发场景：用户想养成某个习惯（早睡、运动、喝水、读书、冥想等）、需要定时提醒、希望用多种方法督促自己。支持创建、管理、停止习惯提醒任务。
---

# 习惯养成提醒

## 概述

帮助用户建立习惯的智能提醒系统。通过多种提醒策略（好处科普、危害警告、放松引导、倒计时、音乐推荐等）轮番轰炸，提高习惯养成的成功率。

## 核心功能

1. **多维度提醒** - 不只是简单通知，而是全方位心理攻势
2. **灵活调度** - 支持cron表达式、间隔提醒、一次性提醒
3. **渠道适配** - 自动识别当前会话渠道进行推送

## 快速开始

### 1. 收集习惯信息

询问用户：
- **习惯名称** - 如：早睡、运动、喝水、读书、冥想
- **目标时间** - 如：23:30睡觉、每天7点起床、每小时喝水
- **提醒频率** - 如：每2分钟、每10分钟、每小时
- **时区** - 默认使用北京时间(Asia/Shanghai)，可询问确认
- **目标渠道** - 从当前会话推断，或询问微信/Telegram等

### 2. 选择提醒策略

根据习惯类型，推荐组合以下策略：

| 策略类型 | 说明 | 适用习惯 |
|---------|------|---------|
| 🎯 基础提醒 | 直接提醒做这件事 | 全部 |
| 💡 好处科普 | 告诉用户坚持的好处 | 全部 |
| ⚠️ 危害警告 | 不做的后果和风险 | 早睡、运动、健康相关 |
| 🧘 放松引导 | 深呼吸、冥想提示 | 早睡、减压、冥想 |
| 🎵 助眠/音乐 | 推荐相关音乐或白噪音 | 早睡、放松 |
| ⏰ 倒计时 | 距离目标时间的倒计时 | 有明确时间目标的习惯 |
| 📊 进度追踪 | 展示坚持了多少天 | 长期习惯 |
| 💬 励志语录 | 相关名言或鼓励 | 全部 |

### 3. 创建定时任务

使用 `openclaw cron add` 创建提醒任务：

```bash
openclaw cron add \
  --name "<habit>-<strategy>" \
  --cron "<cron-expression>" \
  --tz "<timezone>" \
  --channel "<channel>" \
  --to "<destination>" \
  --message "<reminder-message>" \
  --announce
```

**常用cron模式：**
- `*/2 * * * *` - 每2分钟（整点：0,2,4...）
- `*/5 * * * *` - 每5分钟
- `*/10 * * * *` - 每10分钟
- `0 * * * *` - 每小时整点
- `0 22 * * *` - 每天22:00
- `0 22 * * 1-5` - 周一到周五22:00

**避免消息同时到达**：使用错开的cron表达式
- 基础提醒：`*/2 * * * *`（偶数分钟）
- 好处科普：`1-59/2 * * * *`（奇数分钟）
- 危害警告：`0-58/2 * * * *`（错开）

### 4. 管理已有任务

```bash
# 列出所有提醒任务
openclaw cron list

# 禁用某个任务
openclaw cron disable <job-id>

# 启用某个任务
openclaw cron enable <job-id>

# 删除某个任务
openclaw cron rm <job-id>
```

## 预设习惯模板

### 早睡提醒（完整套餐）

目标：23:30入睡，从22:00开始提醒

```bash
# 基础提醒 - 每2分钟
openclaw cron add --name "sleep-reminder" --cron "*/2 22-23 * * *" --tz Asia/Shanghai --channel <channel> --to <destination> --message "🛏️ 早睡提醒：距离23:30睡眠时间越来越近了！放下手机，准备睡觉吧！" --announce

# 好处科普 - 每2分钟（错开）
openclaw cron add --name "sleep-benefits" --cron "1-59/2 22-23 * * *" --tz Asia/Shanghai --channel <channel> --to <destination> --message "💡 早睡的好处：睡眠时大脑会清理代谢废物，让你第二天思维更清晰！" --announce

# 危害警告 - 每2分钟（错开）
openclaw cron add --name "sleep-dangers" --cron "0-58/2 22-23 * * *" --tz Asia/Shanghai --channel <channel> --to <destination> --message "⚠️ 晚睡危害：熬夜会导致免疫力下降、皮肤变差、记忆力衰退！" --announce

# 放松引导 - 每3分钟
openclaw cron add --name "sleep-relax" --cron "*/3 22-23 * * *" --tz Asia/Shanghai --channel <channel> --to <destination> --message "🧘 深呼吸：吸气4秒，屏息7秒，呼气8秒。重复3次。" --announce

# 倒计时 - 每10分钟
openclaw cron add --name "sleep-countdown" --cron "*/10 22-23 * * *" --tz Asia/Shanghai --channel <channel> --to <destination> --message "⏰ 距离23:30目标睡眠时间还有X分钟！开始洗漱准备吧！" --announce
```

### 喝水提醒

目标：每小时喝一杯水

```bash
# 基础提醒 - 每小时
openclaw cron add --name "water-reminder" --cron "0 9-21 * * *" --tz Asia/Shanghai --channel <channel> --to <destination> --message "💧 喝水时间到！站起来走动一下，喝杯水吧～" --announce

# 好处科普 - 每3小时
openclaw cron add --name "water-benefits" --cron "0 10,13,16,19 * * *" --tz Asia/Shanghai --channel <channel> --to <destination> --message "💡 喝水的好处：促进新陈代谢、改善皮肤、帮助排毒、提升精力！" --announce
```

### 运动提醒

目标：每天运动30分钟

```bash
# 晚间运动提醒
openclaw cron add --name "exercise-reminder" --cron "*/10 19-20 * * *" --tz Asia/Shanghai --channel <channel> --to <destination> --message "🏃 运动时间！哪怕只是散步20分钟，也比坐着强！" --announce

# 运动好处
openclaw cron add --name "exercise-benefits" --cron "0 19 * * *" --tz Asia/Shanghai --channel <channel> --to <destination> --message "💡 运动的好处：增强心肺、改善情绪、提高睡眠质量、延缓衰老！" --announce
```

## 停止提醒

当用户想要停止某个习惯提醒时：

```bash
# 查看所有任务
openclaw cron list

# 按名称筛选（习惯相关）
openclaw cron list | grep "<habit>"

# 删除所有相关任务
openclaw cron rm <job-id-1>
openclaw cron rm <job-id-2>
# ...或批量删除
```

## 最佳实践

1. **错开时间** - 避免多条提醒同时到达，使用错开的cron表达式
2. **消息轮换** - 可以创建多条不同消息的同类提醒，让内容更丰富
3. **合理频率** - 高频提醒（每2分钟）适合短时间窗口；低频提醒（每小时）适合全天习惯
4. **时区确认** - 始终确认用户时区，默认Asia/Shanghai
5. **渐进式停止** - 习惯养成后可以逐步减少提醒频率

## 提醒内容素材

在 `references/messages.md` 中有更多可用的提醒内容模板，按习惯类型分类。