<div align="center">

```
          ▲
         ╱█╲            F A N O O S
        ▕███▏           فـانـوس
        ╱▔▔▔╲
       ▕  ✦  ▏          a lantern for designers' portfolios
        ╲___╱
```

**A bilingual (Persian / English) AI portfolio critic and career coach for UI/UX and web designers.**

[![CI](https://github.com/zahednegar-hub/fanoos/actions/workflows/ci.yml/badge.svg)](https://github.com/zahednegar-hub/fanoos/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-0.1.0-f2a93b)

[What it is](#what-it-is) · [Install](#install) · [Quickstart](#quickstart) · [CLI](#cli-reference) · [Roadmap](#roadmap) · [فارسی](#فارسی)

</div>

> **Banner concept.** A single amber lantern (`#f2a93b`) on a deep ink background, its light falling on a
> portfolio grid. Left half Persian, right half English, meeting at the flame. The lantern lights the
> path; it never walks it for you.

---

## What it is

Fanoos (فانوس, *"lantern"*) is an AI agent that reviews a designer's portfolio the way an
international art director would, then tells you exactly what to fix. Point it at a portfolio URL or
PDF and it returns:

- a **one-line Persian verdict**
- **First Impression**: the 10-second recruiter test
- **Critical Issues**: the dealbreakers, each with a fix
- **Quick Wins**: fixes that take under an hour
- **Next 3 Actions**: prioritised
- **Scores** from 0 to 100 on Narrative, Visual Craft, Case Study Depth, English Quality and
  International Readiness

It ships as a CLI (`fanoos review …`) and as an importable Python library.

## Why it exists

Many Iranian and non-native-English designers are talented but lose international jobs,
scholarships and remote clients on presentation: case studies without measurable impact, English
that reads as translated, Persian pages with broken RTL. Good portfolio feedback from someone who
has sat on both sides of the hiring table is rare and expensive.

Fanoos packages that feedback. It reviews against international hiring standards (case study
structure, visual hierarchy, typography, WCAG accessibility and RTL/LTR correctness), checks current
trends with live web and X search before giving trend advice, and never criticises without a
solution. It never invents metrics or clients for you, either.

## Architecture

```
                    fanoos review <url | pdf>
                               │
                               ▼
  ┌────────────────────────────────────────────────────────────┐
  │ cli.py        argparse · .env loading · rich rendering       │
  └──────────────┬────────────────────────────────┬──────────────┘
                 │                                │
                 ▼                                ▼
  ┌──────────────────────────┐      ┌──────────────────────────────┐
  │ sources.py               │      │ agent.py  ·  Fanoos           │
  │  URL → httpx → page text │─────▶│  system_prompt.py (verbatim)  │
  │  PDF → pypdf → page text │      │  + output-format instructions │
  └──────────────────────────┘      │  tools.py: web_search,x_search│
                                    └───────────────┬───────────────┘
                                                    │ streamed Responses API
                                                    ▼
                                  ┌───────────────────────────────────┐
                                  │ xAI API  https://api.x.ai/v1       │
                                  │ Grok runs the search tools itself  │
                                  │ (server-side agent loop)           │
                                  └───────────────┬───────────────────┘
                                                  │ text deltas
                                                  ▼
  ┌────────────────────────────────────────────────────────────────┐
  │ review.py   written review + ```json summary ──▶ Review          │
  │             (falls back to reading Markdown sections)            │
  └────────────────────────────────────────────────────────────────┘
                                  │
                ┌─────────────────┴────────────────┐
                ▼                                  ▼
       terminal report + scorecard          --json structured output
```

| Module | Responsibility |
|---|---|
| `fanoos/system_prompt.py` | The validated persona, verbatim, plus the separate output-format instructions |
| `fanoos/agent.py` | `Fanoos` class: builds the request, streams the reply, maps API errors |
| `fanoos/tools.py` | xAI Agent Tools config (`web_search`, `x_search`) |
| `fanoos/review.py` | `Review` dataclass and the parser for the model's output |
| `fanoos/sources.py` | Reads portfolio input from a URL or a PDF |
| `fanoos/cli.py` | The `fanoos` command |
| `fanoos/errors.py` | Typed errors with actionable messages and exit codes |

## Install

Requires Python 3.10+ on macOS, Linux or Windows.

```bash
git clone https://github.com/zahednegar-hub/fanoos.git
cd fanoos
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
```

Optional extras: `pip install -e ".[bidi]"` for `--bidi` (terminals without right-to-left support),
and `pip install -e ".[dev]"` for tests and linting.

## Quickstart

1. Get an API key at [console.x.ai](https://console.x.ai).
2. Put it in your environment. Fanoos reads the key **only** from `XAI_API_KEY`; it is never
   hard-coded, stored or logged.

   ```bash
   export XAI_API_KEY=xai-...        # Windows PowerShell: $env:XAI_API_KEY = "xai-..."
   ```

   Or copy `.env.example` to `.env` and fill it in (`.env` is git-ignored).

3. Review a portfolio:

   ```bash
   fanoos review https://your-portfolio.com
   fanoos review ~/Desktop/portfolio.pdf --lang en
   fanoos review https://your-portfolio.com --json > review.json
   ```

### As a library

```python
from fanoos import Fanoos, load_source

agent = Fanoos()  # reads XAI_API_KEY
review = agent.review(load_source("https://your-portfolio.com"), language="en")

print(review.verdict)
for issue in review.critical_issues:
    print(issue.issue, "→", issue.fix)
print(review.scores, review.overall_score)
```

See [`examples/review_example.py`](examples/review_example.py) for a streaming example.

## CLI reference

```
fanoos [--version] [--help]
fanoos review <target> [options]
```

| Option | Description |
|---|---|
| `target` | Portfolio URL (`https://…`) or path to a PDF |
| `--lang {fa,en}` | Reply language. Default `fa` (Persian); the verdict is always Persian |
| `--focus TEXT` | Extra request, e.g. `"Focus on the Venture Compass case study"` |
| `--model ID` | Model ID. Default `$FANOOS_MODEL` or `grok-4-1-fast-reasoning` |
| `--json` | Print only the structured review as JSON |
| `--raw` | Print the model's reply unparsed |
| `--no-stream` | Wait for the full reply, then render it as formatted Markdown |
| `--no-fetch` | Don't pre-fetch the URL; let the model open it with web search |
| `--bidi` | Reorder Persian text for terminals without RTL support (needs `[bidi]`) |

| Environment variable | Purpose |
|---|---|
| `XAI_API_KEY` | **Required.** Your xAI API key |
| `FANOOS_MODEL` | Optional default model |

**Exit codes:** `0` success · `2` missing or rejected API key · `3` network failure ·
`4` rate limited (429) · `5` other API error · `6` malformed model output · `7` unreadable input.

## Example output

```
$ fanoos review https://example-portfolio.com --lang en
🏮 Fanoos is reading https://example-portfolio.com …
        پورتفولیوی قوی با روایت ضعیف؛ کیس‌استادی‌ها نتیجه‌ی قابل‌اندازه‌گیری ندارند.

## 1) First Impression
Clean visual hierarchy, but the value proposition is unclear in the first 10 seconds…

## 2) Critical Issues
- No measurable impact in case studies → Add one outcome metric per project.
…

╭─────────────────────── Fanoos · فانوس scorecard ───────────────────────╮
│  Narrative                ████████████░░░░░░░░  62/100                  │
│  Visual Craft             █████████████████░░░  84/100                  │
│  Case Study Depth         ███████████░░░░░░░░░  55/100                  │
│  English Quality          ██████████████░░░░░░  70/100                  │
│  International Readiness  █████████████░░░░░░░  66/100                  │
│                                                                         │
│  Overall                  █████████████░░░░░░░  67/100                  │
│                                                                         │
│  Next 3 Actions                                                         │
│  1. Rewrite Venture Compass case study                                  │
│  2. Fix RTL icons                                                       │
│  3. Polish English bio                                                  │
╰─────────────────────────────────────────────────────────────────────────╯
```

<details>
<summary><code>--json</code> output</summary>

```json
{
  "verdict": "پورتفولیوی قوی با روایت ضعیف؛ کیس‌استادی‌ها نتیجه‌ی قابل‌اندازه‌گیری ندارند.",
  "first_impression": "Clean visual hierarchy, but the value proposition is unclear in the first 10 seconds.",
  "critical_issues": [
    { "issue": "No measurable impact in case studies", "fix": "Add one outcome metric per project." }
  ],
  "quick_wins": ["Add alt text to hero images", "Shorten the About headline"],
  "next_actions": ["Rewrite Venture Compass case study", "Fix RTL icons", "Polish English bio"],
  "scores": {
    "narrative": 62, "visual_craft": 84, "case_study_depth": 55,
    "english_quality": 70, "international_readiness": 66
  },
  "overall_score": 67
}
```

</details>

*The sample above is illustrative, not a review of a real portfolio.*

## Roadmap

- [x] **v0.1**: CLI and library, URL and PDF input, streamed bilingual report, structured JSON
- [ ] **v0.2**: `fanoos polish` for before/after English rewrites of bios and case studies
- [ ] **v0.3**: follow-up re-reviews that compare against a saved previous review
- [ ] **v0.4**: screenshot input, so the model can judge visuals directly
- [ ] **v1.0**: React web interface on the same core, with accounts and payments

## Contributing

Issues and pull requests are welcome.

```bash
pip install -e ".[dev,bidi]"
pytest          # all tests are offline; the API is mocked
ruff check .
```

Please keep the persona in `fanoos/system_prompt.py` verbatim. Behaviour changes belong in the
output-format instructions or in code. Use [Conventional Commits](https://www.conventionalcommits.org/)
(`feat:`, `fix:`, `docs:` …) and add a line to `CHANGELOG.md`.

## License

[MIT](LICENSE) © 2026 Negar Zahed

---

<div dir="rtl">

## فارسی

### فانوس چیست؟

**فانوس** یک دستیار هوش مصنوعی دوزبانه (فارسی/انگلیسی) است که پورتفولیوی طراحان UI/UX و وب را مثل
یک art director بین‌المللی نقد می‌کند و دقیقاً می‌گوید چه چیزی را چطور درست کنید. اسمش یعنی فانوس:
مسیر را روشن می‌کند، اما به جای شما راه نمی‌رود.

یک لینک یا فایل PDF پورتفولیو بدهید و این‌ها را بگیرید:

- **یک جمله حکم کلی به فارسی**
- **First Impression**: تست ۱۰ ثانیه‌ای ریکروتر
- **Critical Issues**: مشکلات اساسی، هرکدام با راه‌حل
- **Quick Wins**: اصلاحاتی که کمتر از یک ساعت وقت می‌برند
- **Next 3 Actions**: سه قدم بعدی به ترتیب اولویت
- **امتیاز ۰ تا ۱۰۰** در پنج معیار: Narrative، Visual Craft، Case Study Depth، English Quality و International Readiness

### چرا ساخته شد؟

خیلی از طراحان ایرانی و غیرانگلیسی‌زبان مهارت دارند، اما فرصت‌های کاری بین‌المللی، بورسیه و کارفرمای
ریموت را به خاطر ارائه از دست می‌دهند: کیس‌استادی بدون نتیجه‌ی قابل‌اندازه‌گیری، انگلیسی‌ای که بوی
ترجمه می‌دهد، یا صفحه‌های فارسی با RTL خراب. فانوس با استانداردهای استخدام بین‌المللی نقد می‌کند،
قبل از توصیه درباره‌ی ترندها با جست‌وجوی زنده در وب و X آن‌ها را بررسی می‌کند، هیچ نقدی را بدون
راه‌حل نمی‌گوید و هرگز عدد، مشتری یا داده‌ی جعلی برای پورتفولیوی شما نمی‌سازد.

### نصب

به Python نسخه‌ی 3.10 یا بالاتر نیاز دارید (macOS، Linux یا Windows).

</div>

```bash
git clone https://github.com/zahednegar-hub/fanoos.git
cd fanoos
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
```

<div dir="rtl">

### شروع سریع

۱. از [console.x.ai](https://console.x.ai) کلید API بگیرید.

۲. کلید را فقط در متغیر محیطی `XAI_API_KEY` بگذارید. فانوس کلید را هیچ‌جا ذخیره یا چاپ نمی‌کند.
می‌توانید فایل `.env.example` را به `.env` کپی کنید و کلید را آنجا بنویسید (فایل `.env` در گیت ثبت نمی‌شود).

۳. پورتفولیو را بررسی کنید:

</div>

```bash
export XAI_API_KEY=xai-...
fanoos review https://your-portfolio.com
fanoos review portfolio.pdf --lang en
fanoos review https://your-portfolio.com --json
```

<div dir="rtl">

### گزینه‌های مهم

| گزینه | توضیح |
|---|---|
| `--lang fa` یا `--lang en` | زبان پاسخ (پیش‌فرض فارسی؛ حکم اول همیشه فارسی است) |
| `--focus "..."` | درخواست اضافه، مثلاً تمرکز روی یک کیس‌استادی |
| `--json` | فقط خروجی ساختاریافته به صورت JSON |
| `--no-stream` | صبر تا پایان پاسخ و نمایش قالب‌بندی‌شده |
| `--bidi` | برای ترمینال‌هایی که متن راست‌به‌چپ را درست نشان نمی‌دهند (مثل کنسول قدیمی ویندوز) |
| `--model` | تغییر مدل (پیش‌فرض `grok-4-1-fast-reasoning`) |

### نقشه‌ی راه

- **نسخه‌ی ۰٫۱**: ابزار خط فرمان و کتابخانه، ورودی لینک و PDF، گزارش دوزبانه و JSON
- **نسخه‌ی ۰٫۲**: دستور `fanoos polish` برای بازنویسی انگلیسی بیو و کیس‌استادی با نسخه‌ی قبل و بعد
- **نسخه‌ی ۰٫۳**: بازبینی دوباره و مقایسه با نقد قبلی
- **نسخه‌ی ۱٫۰**: رابط وب با React روی همین هسته، همراه با حساب کاربری و پرداخت

### مشارکت

پیشنهاد و Pull Request با کمال میل پذیرفته می‌شود. همه‌ی تست‌ها آفلاین هستند و با `pytest` اجرا می‌شوند.
لطفاً متن شخصیت فانوس در `fanoos/system_prompt.py` را دست‌نخورده نگه دارید.

### مجوز

این پروژه با مجوز [MIT](LICENSE) منتشر شده است.

</div>
