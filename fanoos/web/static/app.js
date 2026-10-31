/* Fanoos web UI: i18n, form, report rendering, motion and the 3D lantern.
 * Plain ES module, no build step. All model output is inserted with textContent, never innerHTML. */

const SCORE_KEYS = ["narrative", "visual_craft", "case_study_depth", "english_quality", "international_readiness"];
const NO_LIVE_SEARCH = "بدون جستجوی زنده";
const MAX_BYTES = 15 * 1024 * 1024;
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const I18N = {
  fa: {
    title: "فانوس · Fanoos: منتقد هوش مصنوعی پورتفولیو",
    skip: "پرش به محتوای اصلی",
    "nav.label": "اصلی",
    "nav.menu": "منو",
    "nav.method": "روش کار",
    "nav.criteria": "معیارها",
    "nav.sample": "نمونه گزارش",
    "nav.faq": "پرسش‌ها",
    "nav.start": "شروع بررسی",
    "hero.eyebrow": "منتقد هوش مصنوعی پورتفولیو",
    "hero.title": "راه تو، با نور ما",
    "hero.sub": "فانوس پورتفولیوی طراحی تو را مثل یک art director بین‌المللی می‌خواند، با استانداردهای استخدام جهانی می‌سنجد و برای هر مشکل، راه‌حل می‌دهد.",
    "hero.scroll": "ادامه",
    "form.title": "بررسی پورتفولیو",
    "form.mode": "نوع ورودی",
    "form.modeUrl": "لینک پورتفولیو",
    "form.modePdf": "فایل PDF",
    "form.urlLabel": "لینک پورتفولیو",
    "form.fileLabel": "فایل PDF پورتفولیو",
    "form.fileHint": "فایل را اینجا رها کنید یا کلیک کنید (حداکثر ۱۵ مگابایت)",
    "form.lang": "زبان گزارش",
    "form.submit": "روشن کن",
    "form.submitting": "در حال بررسی…",
    "err.url": "یک لینک کامل وارد کنید؛ مثلاً https://your-portfolio.com",
    "err.file": "یک فایل PDF انتخاب کنید.",
    "err.fileType": "فقط فایل PDF قابل بارگذاری است.",
    "err.fileSize": "حجم فایل بیشتر از ۱۵ مگابایت است.",
    "err.network": "اتصال به سرور فانوس برقرار نشد. مطمئن شوید سرور در حال اجراست.",
    "err.timeout": "بررسی بیش از حد طول کشید. دوباره امتحان کنید.",
    "status.checking": "در حال بررسی تنظیمات…",
    "status.ok": "آماده · {provider} · با جستجوی زنده",
    "status.offline": "آماده · {provider} · بدون جستجوی زنده (سهمیه‌ی رایگان)",
    "status.none": "کلید API تنظیم نشده؛ نمونه گزارش پایین صفحه بدون کلید هم کار می‌کند.",
    "status.down": "سرور در دسترس نیست؛ نمونه گزارش پایین صفحه همچنان قابل مشاهده است.",
    "loading.steps": ["فانوس پورتفولیوی تو را می‌خواند…", "ساختار کیس‌استادی‌ها را می‌سنجد…", "با استانداردهای استخدام بین‌المللی مقایسه می‌کند…", "برای هر مشکل راه‌حل می‌نویسد…"],
    "result.eyebrow": "گزارش تو",
    "result.title": "فانوس روشن شد",
    "criteria.title": "هر پورتفولیو با پنج معیار سنجیده می‌شود",
    "crit.1.t": "روایت", "crit.1.d": "آیا داستان تو در ۱۰ ثانیه فهمیده می‌شود؟",
    "crit.2.t": "کیفیت بصری", "crit.2.d": "سلسله‌مراتب، تایپوگرافی و جزئیات.",
    "crit.3.t": "عمق کیس‌استادی", "crit.3.d": "مسئله، فرایند، راه‌حل، نتیجه.",
    "crit.4.t": "کیفیت انگلیسی", "crit.4.d": "روان، مطمئن و مشخص؛ در سطح native.",
    "crit.5.t": "آمادگی بین‌المللی", "crit.5.d": "برای استخدام، بورسیه و کارفرمای خارجی.",
    "problem.eyebrow": "مسئله",
    "problem.title": "مشکل استعداد نیست؛ ارائه است.",
    "problem.body": "خیلی از طراحان ایرانی مهارتش را دارند، اما فرصت را در همان چند ثانیه‌ی اول از دست می‌دهند: کیس‌استادی بدون نتیجه‌ی قابل‌اندازه‌گیری، انگلیسی‌ای که بوی ترجمه می‌دهد، یا صفحه‌ی فارسی با RTL خراب. ریکروتر وقت حدس زدن ندارد. فانوس همان چیزی را نشانت می‌دهد که او در آن ۱۰ ثانیه می‌بیند.",
    "cta.start": "پورتفولیویم را بررسی کن",
    "cta.sample": "دیدن نمونه گزارش",
    "method.eyebrow": "روش کار",
    "method.title": "از لینک تا نقشه‌ی راه، در کمتر از دو دقیقه",
    "method.1.t": "۱. خواندن", "method.1.d": "لینک یا PDF پورتفولیو را می‌دهی. فانوس متن، ساختار و کیس‌استادی‌ها را می‌خواند.",
    "method.2.t": "۲. سنجیدن", "method.2.d": "در برابر استانداردهای استخدام بین‌المللی، WCAG و درستی RTL/LTR؛ با جستجوی زنده‌ی ترندها روی xAI.",
    "method.3.t": "۳. روشن کردن", "method.3.d": "گزارش با حکم فارسی، مشکلات حیاتی با راه‌حل، اصلاحات زیر یک ساعت، سه قدم بعدی و امتیاز ۰ تا ۱۰۰.",
    "features.eyebrow": "چه می‌گیری",
    "features.title": "نقدی که می‌شود رویش عمل کرد",
    "f.1.t": "تست ۱۰ ثانیه‌ای", "f.1.d": "اولین برداشت یک ریکروتر، صادقانه و مشخص.",
    "f.2.t": "مشکلات حیاتی + راه‌حل", "f.2.d": "هیچ نقدی بدون راه‌حل نیست. هیچ تعریف کلی هم نیست.",
    "f.3.t": "اصلاحات سریع", "f.3.d": "کارهایی که امروز، در کمتر از یک ساعت، انجام می‌شوند.",
    "f.4.t": "سه قدم بعدی", "f.4.d": "نقشه‌ی راه به ترتیب اولویت، نه فهرستی بی‌پایان.",
    "f.5.t": "امتیاز ۰ تا ۱۰۰", "f.5.d": "پنج معیار، تا پیشرفتت را بعد از هر اصلاح ببینی.",
    "f.6.t": "انگلیسی و RTL درست", "f.6.d": "بازنویسی انگلیسی در سطح native و بررسی RTL و دسترس‌پذیری.",
    "sample.eyebrow": "نمونه گزارش",
    "sample.title": "این شکلی روشن می‌شود",
    "sample.lead": "گزارش نمونه برای یک پورتفولیوی فرضی. برای دیدنش کلید API لازم نیست.",
    "faq.eyebrow": "پرسش‌ها",
    "faq.title": "پرسش‌های رایج",
    "faq.1.q": "رایگان است؟",
    "faq.1.a": "فانوس متن‌باز (MIT) است. با کلید رایگان Gemini یا Groq کار می‌کند؛ سهمیه‌ی روزانه محدود است و برای دمو کافی است. برای استفاده‌ی جدی، xAI با جستجوی زنده پیشنهاد می‌شود.",
    "faq.2.q": "چه فرقی بین xAI و ارائه‌دهنده‌های رایگان هست؟",
    "faq.2.a": "روی xAI، فانوس قبل از توصیه درباره‌ی ترندها در وب و X جستجوی زنده می‌کند. روی Gemini و Groq از دانش خود مدل استفاده می‌شود و گزارش با «بدون جستجوی زنده» مشخص می‌شود.",
    "faq.3.q": "پورتفولیو و کلیدهایم کجا می‌روند؟",
    "faq.3.a": "کلیدها فقط از متغیرهای محیطی سرور خوانده می‌شوند و هرگز ذخیره یا نمایش داده نمی‌شوند. محتوای پورتفولیو فقط برای ارائه‌دهنده‌ی هوش مصنوعی انتخاب‌شده فرستاده می‌شود.",
    "faq.4.q": "به چه زبانی جواب می‌دهد؟",
    "faq.4.a": "حکم اول همیشه فارسی است؛ بقیه‌ی گزارش به فارسی یا انگلیسی، به انتخاب تو. اصطلاحات طراحی انگلیسی می‌مانند.",
    "faq.5.q": "عدد و نتیجه برایم می‌سازد؟",
    "faq.5.a": "هرگز. فانوس عدد، مشتری یا داده‌ی ساختگی نمی‌سازد؛ فقط می‌گوید کجا به نتیجه‌ی واقعی نیاز داری و چطور آن را نشان بدهی.",
    "closing.title": "پورتفولیوی تو آماده‌ی دیده شدن است.",
    "closing.body": "فانوس را روشن کن. مسیر را خودت می‌روی.",
    "footer.label": "پانویس",
    "footer.tagline": "منتقد دوزبانه‌ی هوش مصنوعی پورتفولیو برای طراحان UI/UX و وب.",
    "footer.product": "فانوس",
    "footer.project": "پروژه",
    "footer.api": "API",
    "footer.license": "مجوز MIT",
    "footer.made": "ساخته شده با ♥ توسط نگار زاهد",
    "report.verdict": "حکم فانوس",
    "report.overall": "امتیاز کل",
    "report.first": "اولین برداشت",
    "report.issues": "مشکلات حیاتی",
    "report.fix": "راه‌حل:",
    "report.wins": "اصلاحات سریع",
    "report.actions": "سه قدم بعدی",
    "report.scores": "امتیازها",
    "report.full": "متن کامل گزارش",
    "report.sample": "نمونه",
    "report.empty": "موردی گزارش نشد.",
    scores: {
      narrative: "روایت (Narrative)",
      visual_craft: "کیفیت بصری (Visual Craft)",
      case_study_depth: "عمق کیس‌استادی",
      english_quality: "کیفیت انگلیسی",
      international_readiness: "آمادگی بین‌المللی",
    },
  },
  en: {
    title: "Fanoos · فانوس: AI portfolio critic",
    skip: "Skip to main content",
    "nav.label": "Main",
    "nav.menu": "Menu",
    "nav.method": "How it works",
    "nav.criteria": "Criteria",
    "nav.sample": "Sample report",
    "nav.faq": "FAQ",
    "nav.start": "Start a review",
    "hero.eyebrow": "AI portfolio critic",
    "hero.title": "Your path, lit by us",
    "hero.sub": "Fanoos reads your design portfolio the way an international art director would, measures it against global hiring standards, and gives you a fix for every issue.",
    "hero.scroll": "Continue",
    "form.title": "Review a portfolio",
    "form.mode": "Input type",
    "form.modeUrl": "Portfolio URL",
    "form.modePdf": "PDF file",
    "form.urlLabel": "Portfolio URL",
    "form.fileLabel": "Portfolio PDF",
    "form.fileHint": "Drop the file here or click to choose (max 15 MB)",
    "form.lang": "Report language",
    "form.submit": "Light it up",
    "form.submitting": "Reviewing…",
    "err.url": "Enter a full link, for example https://your-portfolio.com",
    "err.file": "Choose a PDF file.",
    "err.fileType": "Only PDF files can be uploaded.",
    "err.fileSize": "The file is larger than 15 MB.",
    "err.network": "Could not reach the Fanoos server. Make sure it is running.",
    "err.timeout": "The review took too long. Please try again.",
    "status.checking": "Checking setup…",
    "status.ok": "Ready · {provider} · with live search",
    "status.offline": "Ready · {provider} · no live search (free tier)",
    "status.none": "No API key configured. The sample report below works without one.",
    "status.down": "Server unreachable. The sample report below still works.",
    "loading.steps": ["Fanoos is reading your portfolio…", "Checking case study structure…", "Comparing with international hiring standards…", "Writing a fix for every issue…"],
    "result.eyebrow": "Your report",
    "result.title": "The lantern is lit",
    "criteria.title": "Every portfolio is measured on five criteria",
    "crit.1.t": "Narrative", "crit.1.d": "Is your story clear in 10 seconds?",
    "crit.2.t": "Visual Craft", "crit.2.d": "Hierarchy, typography and detail.",
    "crit.3.t": "Case Study Depth", "crit.3.d": "Problem, process, solution, impact.",
    "crit.4.t": "English Quality", "crit.4.d": "Concise, confident, native-level.",
    "crit.5.t": "International Readiness", "crit.5.d": "For jobs, scholarships and global clients.",
    "problem.eyebrow": "The problem",
    "problem.title": "Talent isn't the problem. Presentation is.",
    "problem.body": "Many Iranian designers have the skills, yet lose the opportunity in the first few seconds: case studies with no measurable outcome, English that reads as translated, Persian pages with broken RTL. Recruiters don't have time to guess. Fanoos shows you what they see in those 10 seconds.",
    "cta.start": "Review my portfolio",
    "cta.sample": "See a sample report",
    "method.eyebrow": "How it works",
    "method.title": "From a link to a roadmap in under two minutes",
    "method.1.t": "1. Read", "method.1.d": "Share a portfolio URL or PDF. Fanoos reads the copy, the structure and every case study.",
    "method.2.t": "2. Measure", "method.2.d": "Against international hiring standards, WCAG and RTL/LTR correctness, with live trend search on xAI.",
    "method.3.t": "3. Illuminate", "method.3.d": "A report with a Persian verdict, critical issues with fixes, sub-hour wins, the next three actions and 0–100 scores.",
    "features.eyebrow": "What you get",
    "features.title": "Critique you can act on",
    "f.1.t": "The 10-second test", "f.1.d": "A recruiter's first impression, honest and specific.",
    "f.2.t": "Critical issues + fixes", "f.2.d": "No critique without a solution. No vague praise either.",
    "f.3.t": "Quick wins", "f.3.d": "Things you can fix today, in under an hour.",
    "f.4.t": "Next three actions", "f.4.d": "A prioritised roadmap, not an endless list.",
    "f.5.t": "0–100 scores", "f.5.d": "Five criteria, so you can track progress after every fix.",
    "f.6.t": "English and RTL, done right", "f.6.d": "Native-level English rewrites, plus RTL and accessibility checks.",
    "sample.eyebrow": "Sample report",
    "sample.title": "This is what the light shows",
    "sample.lead": "A sample report for a fictional portfolio. No API key needed to see it.",
    "faq.eyebrow": "FAQ",
    "faq.title": "Common questions",
    "faq.1.q": "Is it free?",
    "faq.1.a": "Fanoos is open source (MIT). It runs on a free Gemini or Groq key; free tiers have daily limits that are fine for demos. For serious use, xAI with live search is recommended.",
    "faq.2.q": "What's the difference between xAI and the free providers?",
    "faq.2.a": "On xAI, Fanoos runs live web and X searches before giving trend advice. On Gemini and Groq it uses the model's own knowledge, and the report is marked «بدون جستجوی زنده» (no live search).",
    "faq.3.q": "Where do my portfolio and keys go?",
    "faq.3.a": "Keys are read only from the server's environment variables and are never stored or shown. Portfolio content is sent only to the AI provider you selected.",
    "faq.4.q": "Which language does it answer in?",
    "faq.4.a": "The opening verdict is always Persian; the rest is in Persian or English, your choice. Design terms stay in English.",
    "faq.5.q": "Will it invent numbers or results for me?",
    "faq.5.a": "Never. Fanoos does not invent metrics, clients or data. It tells you where you need real outcomes and how to show them.",
    "closing.title": "Your portfolio is ready to be seen.",
    "closing.body": "Light the lantern. You walk the path.",
    "footer.label": "Footer",
    "footer.tagline": "A bilingual AI portfolio critic for UI/UX and web designers.",
    "footer.product": "Fanoos",
    "footer.project": "Project",
    "footer.api": "API",
    "footer.license": "MIT License",
    "footer.made": "Made with ♥ by Negar Zahed",
    "report.verdict": "Fanoos verdict",
    "report.overall": "Overall",
    "report.first": "First impression",
    "report.issues": "Critical issues",
    "report.fix": "Fix:",
    "report.wins": "Quick wins",
    "report.actions": "Next 3 actions",
    "report.scores": "Scores",
    "report.full": "Full written report",
    "report.sample": "Sample",
    "report.empty": "Nothing reported.",
    scores: {
      narrative: "Narrative",
      visual_craft: "Visual Craft",
      case_study_depth: "Case Study Depth",
      english_quality: "English Quality",
      international_readiness: "International Readiness",
    },
  },
};

// Hardcoded demo data for a fictional portfolio, so the page is complete without an API key.
const SAMPLE = {
  fa: {
    verdict: "پایه‌ی بصری قوی است، اما کیس‌استادی‌ها هنوز داستانِ «چرا» و «چه نتیجه‌ای» را تعریف نمی‌کنند.",
    first_impression: "در ۱۰ ثانیه‌ی اول، کیفیت بصری و نظم گرید دیده می‌شود، اما معلوم نیست طراح دقیقاً چه نقشی دارد و دنبال چه موقعیتی است. Hero بیشتر از آنکه «چه مشکلی را حل می‌کنم» بگوید، «چه ابزارهایی بلدم» را می‌گوید.",
    critical_issues: [
      { issue: "کیس‌استادی‌ها نتیجه‌ی قابل‌اندازه‌گیری ندارند و با تصویر نهایی تمام می‌شوند.", fix: "به هر پروژه یک بخش Outcome اضافه کن: یک عدد واقعی (مثلاً نرخ تکمیل ثبت‌نام) یا اگر عدد نداری، بازخورد کاربر یا تصمیمی که تیم بر اساس طراحی تو گرفت." },
      { issue: "نقش تو در پروژه‌های تیمی مشخص نیست.", fix: "زیر عنوان هر کیس‌استادی یک خط بنویس: Role، Team، Timeline، و دقیقاً کدام تصمیم‌ها مال تو بود." },
      { issue: "در نسخه‌ی فارسی، آیکون‌های جهت‌دار (فلش‌ها و chevron ها) آینه نشده‌اند و ترتیب breadcrumb برعکس است.", fix: "آیکون‌های جهت‌دار را در dir=\"rtl\" با transform: scaleX(-1) آینه کن و ترتیب breadcrumb را از راست به چپ بچین." },
    ],
    quick_wins: [
      "متن Hero را به یک جمله‌ی ارزش تبدیل کن: «طراح محصول برای اپ‌های فین‌تک فارسی‌زبان».",
      "برای همه‌ی تصاویر کاور alt text معنادار بنویس.",
      "کنتراست متن خاکستری روی پس‌زمینه‌ی روشن را به حداقل ۴.۵:۱ برسان.",
      "لینک رزومه‌ی PDF را در هدر قرار بده، نه فقط در فوتر.",
    ],
    next_actions: [
      "کیس‌استادی اصلی را با ساختار Problem → Process → Solution → Impact بازنویسی کن.",
      "بیو و Hero انگلیسی را به انگلیسی native و مشخص بازنویسی کن (نسخه‌ی قبل و بعد).",
      "یک بازبینی کامل RTL و دسترس‌پذیری روی نسخه‌ی فارسی انجام بده.",
    ],
    scores: { narrative: 58, visual_craft: 84, case_study_depth: 52, english_quality: 68, international_readiness: 63 },
    live_search: true,
    provider: "sample",
    model: "",
  },
  en: {
    verdict: "پایه‌ی بصری قوی است، اما کیس‌استادی‌ها هنوز داستانِ «چرا» و «چه نتیجه‌ای» را تعریف نمی‌کنند.",
    first_impression: "In the first 10 seconds the visual craft and grid discipline come through, but it is unclear what role the designer plays and what job they want. The hero lists tools instead of saying which problem they solve.",
    critical_issues: [
      { issue: "Case studies end on the final screens, with no measurable outcome.", fix: "Add an Outcome section to every project: one real number (for example sign-up completion rate) or, without data, user feedback or a decision the team made because of your work." },
      { issue: "Your role in team projects is unclear.", fix: "Under each case study title, add one line: Role, Team, Timeline, and exactly which decisions were yours." },
      { issue: "In the Persian version, directional icons (arrows, chevrons) are not mirrored and the breadcrumb order is reversed.", fix: "Mirror directional icons under dir=\"rtl\" with transform: scaleX(-1) and order the breadcrumb right to left." },
    ],
    quick_wins: [
      "Turn the hero into one value statement: “Product designer for Persian-language fintech apps.”",
      "Write meaningful alt text for every cover image.",
      "Raise grey body text on light backgrounds to at least 4.5:1 contrast.",
      "Put the PDF résumé link in the header, not only in the footer.",
    ],
    next_actions: [
      "Rewrite the lead case study as Problem → Process → Solution → Impact.",
      "Rewrite the English bio and hero in concise, native-level English (before/after).",
      "Run a full RTL and accessibility pass on the Persian version.",
    ],
    scores: { narrative: 58, visual_craft: 84, case_study_depth: 52, english_quality: 68, international_readiness: 63 },
    live_search: true,
    provider: "sample",
    model: "",
  },
};

const $ = (sel, root = document) => root.querySelector(sel);
const state = { lang: "fa", lastReview: null, health: null, loadingTimer: null, lantern: null };

const t = (key) => {
  const value = I18N[state.lang][key];
  return value === undefined ? I18N.fa[key] : value;
};
const num = (n) => (state.lang === "fa" ? Number(n).toLocaleString("fa-IR") : String(n));

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "text") node.textContent = value;
    else if (key === "class") node.className = value;
    else node.setAttribute(key, value);
  }
  for (const child of [].concat(children)) if (child) node.append(child);
  return node;
}

/* i18n -------------------------------------------------------------------------------------------- */

function applyLang(lang) {
  state.lang = lang;
  const html = document.documentElement;
  html.lang = lang;
  html.dir = lang === "fa" ? "rtl" : "ltr";
  document.title = t("title");
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    if (node.dataset.i18n === "footer.made") renderMadeWith(node);
    else node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-attr]").forEach((node) => {
    const [attr, key] = node.dataset.i18nAttr.split(":");
    node.setAttribute(attr, t(key));
  });
  const toggle = $("#lang-toggle");
  toggle.textContent = lang === "fa" ? "EN" : "فا";
  toggle.lang = lang === "fa" ? "en" : "fa";
  // The accessible name starts with the visible text (WCAG 2.5.3).
  toggle.setAttribute("aria-label", lang === "fa" ? "EN — English" : "فا — فارسی");
  $(`#lang-${lang}`).checked = true; // the report language follows the interface unless changed
  try { localStorage.setItem("fanoos.lang", lang); } catch { /* private mode */ }
  if (!fileInput.files.length) $("#file-name").textContent = t("form.fileHint");
  renderSample();
  if (state.lastReview) renderReport($("#result-report"), state.lastReview, false);
  renderStatus();
  frameLantern();
}

function renderMadeWith(node) {
  const [before, after] = t("footer.made").split("♥");
  node.replaceChildren(before, el("span", { class: "heart", "aria-hidden": "true", text: "♥" }), after);
}

/* Report rendering -------------------------------------------------------------------------------- */

const textBlock = (tag, text, cls) => el(tag, { class: cls || "", dir: "auto", text });

function card(title, index, body) {
  const head = el("h3", {}, [el("span", { class: "num", "aria-hidden": "true", text: num(index) }), t(title)]);
  return el("section", { class: "card" }, [head, body]);
}

function listOrEmpty(items, build) {
  return items && items.length ? build(items) : textBlock("p", t("report.empty"), "muted");
}

function renderReport(container, review, animate = true, isSample = false) {
  const scores = review.scores || {};
  const values = SCORE_KEYS.filter((k) => typeof scores[k] === "number").map((k) => scores[k]);
  const overall = values.length ? Math.round(values.reduce((a, b) => a + b, 0) / values.length) : null;

  const meta = el("p", { class: "report-meta" });
  if (isSample) meta.append(el("span", { class: "chip", lang: state.lang, text: t("report.sample") }));
  if (review.provider && review.provider !== "sample") meta.append(el("span", { class: "chip", text: review.provider }));
  if (review.model) meta.append(el("span", { class: "chip", text: review.model }));
  if (review.live_search === false) meta.append(el("span", { class: "chip", lang: "fa", text: NO_LIVE_SEARCH }));

  const ring = el("div", { class: "ring", role: "img", "aria-label": `${t("report.overall")}: ${overall ?? "–"}/100` }, [
    el("div", { class: "ring-inner" }, [el("span", { class: "ring-value", text: overall === null ? "–" : num(overall) })]),
  ]);
  const head = el("header", { class: "report-head" }, [
    el("div", {}, [
      el("p", { class: "verdict-label", text: t("report.verdict") }),
      el("p", { class: "verdict", lang: "fa", dir: "rtl", text: review.verdict || "" }),
      meta.childNodes.length ? meta : null,
    ]),
    overall === null ? null : el("div", { class: "overall" }, [ring, el("span", { class: "ring-label", text: t("report.overall") })]),
  ]);

  const first = card("report.first", 1, textBlock("p", review.first_impression || t("report.empty")));
  const issues = card("report.issues", 2, listOrEmpty(review.critical_issues, (items) =>
    el("ul", { class: "issues" }, items.map((item) => el("li", { class: "issue" }, [
      textBlock("p", item.issue, "issue-title"),
      item.fix ? el("p", { class: "issue-fix" }, [el("strong", { text: t("report.fix") }), el("bdi", { text: item.fix })]) : null,
    ])))));
  const wins = card("report.wins", 3, listOrEmpty(review.quick_wins, (items) =>
    el("ul", { class: "bullets" }, items.map((w) => textBlock("li", w)))));
  const actions = card("report.actions", 4, listOrEmpty(review.next_actions, (items) =>
    el("ol", { class: "steps" }, items.map((a) => textBlock("li", a)))));

  const bars = el("div", { class: "scores" }, SCORE_KEYS.filter((k) => k in scores).map((key) => {
    const value = scores[key];
    const fill = el("div", { class: `bar-fill ${value >= 75 ? "is-high" : value >= 50 ? "is-mid" : "is-low"}` });
    fill.dataset.value = value;
    const label = I18N[state.lang].scores[key];
    return el("div", { class: "score-row" }, [
      el("div", { class: "score-top" }, [
        el("span", { class: "score-name", text: label }),
        el("span", { class: "score-value", text: `${num(value)}/${num(100)}` }),
      ]),
      el("div", { class: "bar", role: "meter", "aria-valuemin": "0", "aria-valuemax": "100", "aria-valuenow": String(value), "aria-label": label }, [fill]),
    ]);
  }));
  const scoresCard = card("report.scores", 5, values.length ? bars : textBlock("p", t("report.empty")));

  const grid = el("div", { class: "report-grid" }, [
    el("div", { class: "report-col" }, [first, issues]),
    el("div", { class: "report-col" }, [scoresCard, actions, wins]),
  ]);

  const parts = [head, grid];
  if (review.live_search === false) parts.push(el("p", { class: "report-footnote", lang: "fa", dir: "rtl", text: NO_LIVE_SEARCH }));
  if (review.report) {
    parts.push(el("details", { class: "full-report" }, [el("summary", { text: t("report.full") }), el("pre", { dir: "auto", text: review.report })]));
  }

  const article = el("article", { class: "report", "aria-label": isSample ? t("sample.title") : t("result.title") }, parts);
  container.replaceChildren(article);
  revealScores(article, ring, overall, animate && !reducedMotion);
}

function revealScores(article, ring, overall, animate) {
  const reveal = () => {
    article.querySelectorAll(".bar-fill").forEach((fill) => { fill.style.width = `${fill.dataset.value}%`; });
    ring.style.setProperty("--value", overall ?? 0);
  };
  if (!animate) {
    article.querySelectorAll(".bar-fill").forEach((f) => { f.style.transition = "none"; });
    ring.style.transition = "none";
    reveal();
    return;
  }
  const io = new IntersectionObserver((entries) => {
    if (entries.some((e) => e.isIntersecting)) { requestAnimationFrame(reveal); io.disconnect(); }
  }, { threshold: 0.2 });
  io.observe(article);
}

let sampleShown = false;
function renderSample() {
  renderReport($("#sample-report"), SAMPLE[state.lang], !sampleShown, true);
  sampleShown = true;
}

/* Provider status ------------------------------------------------------------------------------------- */

async function loadHealth() {
  try {
    const res = await fetch("/health", { headers: { Accept: "application/json" } });
    state.health = res.ok ? await res.json() : { status: "down" };
  } catch {
    state.health = { status: "down" };
  }
  renderStatus();
}

function renderStatus() {
  const node = $("#provider-status");
  node.className = "form-status";
  const h = state.health;
  if (!h) { node.textContent = t("status.checking"); return; }
  if (h.status !== "ok") { node.textContent = t("status.down"); node.classList.add("is-warn"); return; }
  if (!h.provider) { node.textContent = t("status.none"); node.classList.add("is-warn"); return; }
  node.textContent = t(h.live_search ? "status.ok" : "status.offline").replace("{provider}", h.provider);
  node.classList.add("is-ok");
}

/* Form ------------------------------------------------------------------------------------------------- */

const form = $("#review-form");
const urlInput = $("#url");
const fileInput = $("#file");
const dropzone = $("#dropzone");
const errorBox = $("#form-error");
const submitBtn = $("#submit");
const mode = () => form.elements.mode.value;

function setMode(value) {
  const isUrl = value === "url";
  $("#field-url").hidden = !isUrl;
  $("#field-pdf").hidden = isUrl;
  hideError();
}
function showError(message) { errorBox.textContent = message; errorBox.hidden = false; }
function hideError() { errorBox.hidden = true; errorBox.textContent = ""; urlInput.removeAttribute("aria-invalid"); }

// Server errors are "English\nPersian": show the line(s) for the current language.
function localise(message) {
  const lines = String(message || "").split("\n").filter(Boolean);
  if (lines.length < 2) return lines[0] || "";
  const isFa = (l) => /[؀-ۿ]/.test(l);
  return lines.filter((l) => (state.lang === "fa" ? isFa(l) : !isFa(l))).join("\n") || lines.join("\n");
}

function setFile(file) {
  hideError();
  if (!file) return;
  if (!/\.pdf$/i.test(file.name) && file.type !== "application/pdf") { showError(t("err.fileType")); return; }
  if (file.size > MAX_BYTES) { showError(t("err.fileSize")); return; }
  const dt = new DataTransfer();
  dt.items.add(file);
  fileInput.files = dt.files;
  $("#file-name").textContent = file.name;
  dropzone.classList.add("has-file");
}

function validate() {
  if (mode() === "url") {
    let ok = false;
    try { ok = /^https?:$/.test(new URL(urlInput.value.trim()).protocol); } catch { ok = false; }
    if (!ok) { urlInput.setAttribute("aria-invalid", "true"); showError(t("err.url")); urlInput.focus(); return false; }
  } else if (!fileInput.files.length) {
    showError(t("err.file"));
    dropzone.focus();
    return false;
  }
  return true;
}

// While a review runs the user stays in the hero: the lantern works harder and the status line narrates.
function startLoading() {
  const steps = t("loading.steps");
  let i = 0;
  $("#form-progress").hidden = false;
  $("#loading-text").textContent = steps[0];
  state.loadingTimer = setInterval(() => {
    i = (i + 1) % steps.length;
    $("#loading-text").textContent = t("loading.steps")[i];
  }, 3200);
  submitBtn.disabled = true;
  submitBtn.firstElementChild.textContent = t("form.submitting");
  state.lantern?.setMode("thinking");
}

function stopLoading(success) {
  clearInterval(state.loadingTimer);
  $("#form-progress").hidden = true;
  submitBtn.disabled = false;
  submitBtn.firstElementChild.textContent = t("form.submit");
  state.lantern?.setMode(success ? "done" : "idle");
}

async function submit(event) {
  event.preventDefault();
  hideError();
  if (!validate()) return;

  const body = new FormData();
  body.append("lang", form.elements.lang.value);
  if (mode() === "url") body.append("url", urlInput.value.trim());
  else body.append("file", fileInput.files[0]);

  startLoading();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 5 * 60 * 1000);
  try {
    const res = await fetch("/api/review", { method: "POST", body, signal: controller.signal });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      stopLoading(false);
      showError(localise(data.error) || `HTTP ${res.status}`);
      return;
    }
    stopLoading(true);
    state.lastReview = data;
    const result = $("#result");
    result.hidden = false;
    renderReport($("#result-report"), data, true);
    // Give the flare a beat, then move to the report.
    setTimeout(() => {
      result.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
      $("#result-title").focus({ preventScroll: true });
    }, reducedMotion ? 0 : 450);
  } catch (err) {
    stopLoading(false);
    showError(err.name === "AbortError" ? t("err.timeout") : t("err.network"));
  } finally {
    clearTimeout(timer);
  }
}

/* Header, menu, motion ----------------------------------------------------------------------------------- */

const header = $("#site-header");
const nav = $("#site-nav");
const menuBtn = $("#menu-toggle");

function setMenu(open) {
  menuBtn.setAttribute("aria-expanded", String(open));
  nav.classList.toggle("is-open", open);
  header.classList.toggle("is-open", open);
}
menuBtn.addEventListener("click", () => setMenu(menuBtn.getAttribute("aria-expanded") !== "true"));
nav.addEventListener("click", (e) => { if (e.target.closest("a")) setMenu(false); });
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && nav.classList.contains("is-open")) { setMenu(false); menuBtn.focus(); }
});
window.matchMedia("(min-width: 900px)").addEventListener("change", (e) => { if (e.matches) setMenu(false); });

const hero = $("#top");
let ticking = false;
function onScroll() {
  if (ticking) return;
  ticking = true;
  requestAnimationFrame(() => {
    ticking = false;
    header.classList.toggle("is-scrolled", window.scrollY > 24);
    const progress = Math.min(1, Math.max(0, window.scrollY / (hero.offsetHeight || 1)));
    state.lantern?.setScroll(progress);
  });
}
window.addEventListener("scroll", onScroll, { passive: true });

function initReveal() {
  if (reducedMotion || !("IntersectionObserver" in window)) return;
  document.documentElement.classList.add("motion");
  const io = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) { entry.target.classList.add("is-visible"); io.unobserve(entry.target); }
    }
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.12 });
  document.querySelectorAll("[data-reveal]").forEach((node) => io.observe(node));
}

// "How it works": the step nearest the middle of the viewport is lit.
function initSteps() {
  const steps = [...document.querySelectorAll("[data-step]")];
  if (!steps.length) return;
  document.documentElement.classList.add("steps-js");
  const activate = (step) => steps.forEach((s) => s.classList.toggle("is-active", s === step));
  activate(steps[0]);
  const io = new IntersectionObserver((entries) => {
    const hit = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (hit) activate(hit.target);
  }, { rootMargin: "-42% 0px -42% 0px", threshold: [0, 0.5, 1] });
  steps.forEach((s) => io.observe(s));
}

/* The lantern ----------------------------------------------------------------------------------------- */

// Desktop: the lantern stands beside the copy (left in Persian, right in English). Mobile: above it.
function frameLantern() {
  if (!state.lantern) return;
  const wide = window.matchMedia("(min-width: 960px)").matches;
  if (wide) state.lantern.setFraming(state.lang === "fa" ? -0.2 : 0.2, 0);
  else state.lantern.setFraming(0, -0.2);
}

async function initLantern() {
  const stage = $("#lantern-stage");
  try {
    const { mountLantern } = await import("/static/lantern3d.js");
    state.lantern = mountLantern(stage, { reducedMotion, quality: new URLSearchParams(location.search).get("quality") || "auto" });
  } catch (err) {
    console.warn("Fanoos: 3D lantern unavailable, showing the static mark.", err);
    state.lantern = null;
  }
  stage.dataset.lantern = state.lantern ? "webgl" : "fallback";
  if (state.lantern) {
    frameLantern();
    window.matchMedia("(min-width: 960px)").addEventListener("change", frameLantern);
    onScroll();
  }
  window.__fanoos = { lantern: state.lantern }; // for automated UI checks
}

/* Wire up ------------------------------------------------------------------------------------------------- */

form.addEventListener("submit", submit);
form.elements.mode.forEach((radio) => radio.addEventListener("change", () => setMode(radio.value)));
urlInput.addEventListener("input", hideError);
fileInput.addEventListener("change", () => setFile(fileInput.files[0]));
["dragenter", "dragover"].forEach((type) => dropzone.addEventListener(type, (e) => { e.preventDefault(); dropzone.classList.add("is-dragover"); }));
["dragleave", "drop"].forEach((type) => dropzone.addEventListener(type, (e) => { e.preventDefault(); dropzone.classList.remove("is-dragover"); }));
dropzone.addEventListener("drop", (e) => setFile(e.dataTransfer.files[0]));
dropzone.tabIndex = 0;
dropzone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); } });
$("#lang-toggle").addEventListener("click", () => applyLang(state.lang === "fa" ? "en" : "fa"));

let saved = null;
try { saved = localStorage.getItem("fanoos.lang"); } catch { /* private mode */ }
const params = new URLSearchParams(location.search);
applyLang(params.get("lang") === "en" || (!params.get("lang") && saved === "en") ? "en" : "fa");
initReveal();
initSteps();
onScroll();
loadHealth();
initLantern();
