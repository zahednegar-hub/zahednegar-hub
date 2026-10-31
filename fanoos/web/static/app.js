/* Fanoos web UI: i18n, form handling, report rendering. No framework, no build step.
 * All model output is inserted with textContent, never innerHTML. */
(() => {
  "use strict";

  const SCORE_KEYS = ["narrative", "visual_craft", "case_study_depth", "english_quality", "international_readiness"];
  const NO_LIVE_SEARCH = "بدون جستجوی زنده";
  const MAX_BYTES = 15 * 1024 * 1024;

  const I18N = {
    fa: {
      title: "فانوس · Fanoos: منتقد هوش مصنوعی پورتفولیو",
      skip: "پرش به محتوای اصلی",
      "nav.label": "اصلی",
      "nav.about": "فانوس چیست",
      "nav.sample": "نمونه گزارش",
      "nav.start": "شروع",
      "hero.eyebrow": "منتقد هوش مصنوعی پورتفولیو برای طراحان UI/UX و وب",
      "hero.title": "راه تو، با نور ما",
      "hero.sub": "پورتفولیوی خودت را بده؛ فانوس آن را با استانداردهای استخدام بین‌المللی نقد می‌کند و برای هر مشکل، راه‌حل می‌دهد.",
      "form.title": "بررسی پورتفولیو",
      "form.mode": "نوع ورودی",
      "form.modeUrl": "لینک پورتفولیو",
      "form.modePdf": "فایل PDF",
      "form.modeHint": "یکی را انتخاب کنید: لینک وب‌سایت یا فایل PDF.",
      "form.urlLabel": "لینک پورتفولیو",
      "form.fileLabel": "فایل PDF پورتفولیو",
      "form.fileHint": "فایل را اینجا رها کنید یا برای انتخاب کلیک کنید (حداکثر ۱۵ مگابایت)",
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
      "status.ok": "آماده · {provider}",
      "status.offline": "{provider} · بدون جستجوی زنده (سهمیه‌ی رایگان)",
      "status.none": "کلید API تنظیم نشده؛ نمونه گزارش پایین صفحه بدون کلید هم کار می‌کند.",
      "status.down": "سرور در دسترس نیست؛ نمونه گزارش پایین صفحه همچنان قابل مشاهده است.",
      "result.title": "گزارش فانوس",
      "loading.sub": "یک بررسی دقیق معمولاً بین ۳۰ ثانیه تا ۲ دقیقه طول می‌کشد.",
      "loading.steps": ["در حال خواندن پورتفولیو…", "بررسی ساختار کیس‌استادی‌ها…", "سنجش با استانداردهای استخدام بین‌المللی…", "نوشتن راه‌حل برای هر مشکل…"],
      "about.title": "فانوس چیست",
      "about.lead": "فانوس یک art director دوزبانه است که صدها پورتفولیو را از هر دو سوی میز استخدام دیده. مسیر را روشن می‌کند، اما به جای تو راه نمی‌رود.",
      "about.f1.title": "تست ۱۰ ثانیه‌ای ریکروتر",
      "about.f1.body": "اولین برداشت، مشکلات حیاتی، اصلاحات زیر یک ساعت و سه قدم بعدی، با ترتیب اولویت.",
      "about.f2.title": "برای هر نقد، یک راه‌حل",
      "about.f2.body": "بدون تعریف کلی و بدون عدد ساختگی. هر مشکل همراه با اصلاح مشخص می‌آید.",
      "about.f3.title": "استاندارد بین‌المللی، نگاه فارسی",
      "about.f3.body": "ساختار کیس‌استادی، تایپوگرافی، WCAG، درستی RTL/LTR و انگلیسی در سطح native.",
      "sample.title": "نمونه گزارش",
      "sample.lead": "یک گزارش نمونه برای یک پورتفولیوی فرضی. برای دیدنش به کلید API نیاز ندارید.",
      "footer.made": "ساخته شده با ♥ توسط نگار زاهد",
      "footer.license": "مجوز MIT",
      "report.verdict": "حکم فانوس",
      "report.overall": "امتیاز کل",
      "report.first": "اولین برداشت",
      "report.firstSub": "تست ۱۰ ثانیه‌ای ریکروتر",
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
      "nav.about": "What is Fanoos",
      "nav.sample": "Sample report",
      "nav.start": "Start",
      "hero.eyebrow": "AI portfolio critic for UI/UX and web designers",
      "hero.title": "Your path, lit by us",
      "hero.sub": "Share your portfolio. Fanoos reviews it against international hiring standards and gives you a fix for every issue.",
      "form.title": "Review a portfolio",
      "form.mode": "Input type",
      "form.modeUrl": "Portfolio URL",
      "form.modePdf": "PDF file",
      "form.modeHint": "Choose one: a website link or a PDF file.",
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
      "status.ok": "Ready · {provider}",
      "status.offline": "{provider} · no live search (free tier)",
      "status.none": "No API key configured. The sample report below works without one.",
      "status.down": "Server unreachable. The sample report below still works.",
      "result.title": "Your Fanoos report",
      "loading.sub": "A thorough review usually takes 30 seconds to 2 minutes.",
      "loading.steps": ["Reading your portfolio…", "Checking case study structure…", "Measuring against international hiring standards…", "Writing a fix for every issue…"],
      "about.title": "What is Fanoos",
      "about.lead": "Fanoos is a bilingual art director who has seen hundreds of portfolios from both sides of the hiring table. It lights the path; it never walks it for you.",
      "about.f1.title": "The 10-second recruiter test",
      "about.f1.body": "First impression, critical issues, fixes under an hour and the next three actions, in priority order.",
      "about.f2.title": "A fix for every critique",
      "about.f2.body": "No vague praise and no invented numbers. Every issue comes with a specific fix.",
      "about.f3.title": "Global standards, Persian-aware",
      "about.f3.body": "Case study structure, typography, WCAG, RTL/LTR correctness and native-level English.",
      "sample.title": "Sample report",
      "sample.lead": "A sample report for a fictional portfolio. No API key needed to see it.",
      "footer.made": "Made with ♥ by Negar Zahed",
      "footer.license": "MIT License",
      "report.verdict": "Fanoos verdict",
      "report.overall": "Overall",
      "report.first": "First impression",
      "report.firstSub": "The 10-second recruiter test",
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
  const state = { lang: "fa", lastReview: null, health: null, loadingTimer: null };

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

  /* i18n ------------------------------------------------------------------------------------------------ */

  function applyLang(lang) {
    state.lang = lang;
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "fa" ? "rtl" : "ltr";
    document.title = t("title");
    document.querySelectorAll("[data-i18n]").forEach((node) => {
      const key = node.dataset.i18n;
      if (key === "footer.made") {
        renderMadeWith(node);
      } else {
        node.textContent = t(key);
      }
    });
    document.querySelectorAll("[data-i18n-attr]").forEach((node) => {
      const [attr, key] = node.dataset.i18nAttr.split(":");
      node.setAttribute(attr, t(key));
    });
    const toggle = $("#lang-toggle");
    toggle.textContent = lang === "fa" ? "English" : "فارسی";
    toggle.lang = lang === "fa" ? "en" : "fa";
    toggle.setAttribute("aria-label", lang === "fa" ? "Switch to English" : "تغییر زبان به فارسی");
    // The report language follows the interface language unless the user changes it.
    $(`#lang-${lang}`).checked = true;
    try { localStorage.setItem("fanoos.lang", lang); } catch { /* private mode */ }
    if (!fileInput.files.length) $("#file-name").textContent = t("form.fileHint");
    renderSample();
    if (state.lastReview) renderReport($("#result-report"), state.lastReview, false);
    renderStatus();
  }

  function renderMadeWith(node) {
    const [before, after] = t("footer.made").split("♥");
    node.replaceChildren(before, el("span", { class: "heart", "aria-hidden": "true", text: "♥" }), after);
  }

  /* Report rendering ------------------------------------------------------------------------------------ */

  function textBlock(tag, text, cls) {
    return el(tag, { class: cls || "", dir: "auto", text });
  }

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
      return el("div", { class: "score-row" }, [
        el("div", { class: "score-top" }, [
          el("span", { class: "score-name", text: I18N[state.lang].scores[key] }),
          el("span", { class: "score-value", text: `${num(value)}/${num(100)}` }),
        ]),
        el("div", { class: "bar", role: "meter", "aria-valuemin": "0", "aria-valuemax": "100", "aria-valuenow": String(value), "aria-label": I18N[state.lang].scores[key] }, [fill]),
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

    const article = el("article", { class: "report", "aria-label": t("result.title") }, parts);
    container.replaceChildren(article);
    revealScores(article, ring, overall, animate);
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
    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver((entries) => {
        if (entries.some((e) => e.isIntersecting)) { requestAnimationFrame(reveal); io.disconnect(); }
      }, { threshold: 0.2 });
      io.observe(article);
    } else {
      requestAnimationFrame(reveal);
    }
  }

  let sampleShown = false;
  function renderSample() {
    renderReport($("#sample-report"), SAMPLE[state.lang], !sampleShown, true);
    sampleShown = true;
  }

  /* Provider status --------------------------------------------------------------------------------------- */

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
    const key = h.live_search ? "status.ok" : "status.offline";
    node.textContent = t(key).replace("{provider}", h.provider);
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

  function showError(message) {
    errorBox.textContent = message;
    errorBox.hidden = false;
  }
  function hideError() {
    errorBox.hidden = true;
    errorBox.textContent = "";
    urlInput.removeAttribute("aria-invalid");
  }

  // Server errors are "English\nPersian": show the line for the current language.
  function localise(message) {
    const lines = String(message || "").split("\n").filter(Boolean);
    if (lines.length < 2) return lines[0] || "";
    const persian = lines.filter((l) => /[؀-ۿ]/.test(l));
    const english = lines.filter((l) => !/[؀-ۿ]/.test(l));
    return (state.lang === "fa" ? persian : english).join("\n") || lines.join("\n");
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
      const value = urlInput.value.trim();
      let ok = false;
      try { ok = /^https?:$/.test(new URL(value).protocol); } catch { ok = false; }
      if (!ok) { urlInput.setAttribute("aria-invalid", "true"); showError(t("err.url")); urlInput.focus(); return false; }
    } else if (!fileInput.files.length) {
      showError(t("err.file"));
      dropzone.focus();
      return false;
    }
    return true;
  }

  function startLoading() {
    const result = $("#result");
    result.hidden = false;
    $("#loading").hidden = false;
    $("#result-report").replaceChildren();
    const steps = t("loading.steps");
    let i = 0;
    $("#loading-text").textContent = steps[0];
    state.loadingTimer = setInterval(() => {
      i = (i + 1) % steps.length;
      $("#loading-text").textContent = t("loading.steps")[i];
    }, 3500);
    submitBtn.disabled = true;
    submitBtn.firstElementChild.textContent = t("form.submitting");
    result.scrollIntoView({ block: "start" });
  }

  function stopLoading() {
    clearInterval(state.loadingTimer);
    $("#loading").hidden = true;
    submitBtn.disabled = false;
    submitBtn.firstElementChild.textContent = t("form.submit");
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
      stopLoading();
      if (!res.ok) {
        $("#result").hidden = true;
        showError(localise(data.error) || `HTTP ${res.status}`);
        form.scrollIntoView({ block: "center" });
        return;
      }
      state.lastReview = data;
      renderReport($("#result-report"), data, true);
      $("#result-title").focus?.();
    } catch (err) {
      stopLoading();
      $("#result").hidden = true;
      showError(err.name === "AbortError" ? t("err.timeout") : t("err.network"));
    } finally {
      clearTimeout(timer);
    }
  }

  /* Wire up --------------------------------------------------------------------------------------------- */

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
  $("#result-title").tabIndex = -1;

  let saved = null;
  try { saved = localStorage.getItem("fanoos.lang"); } catch { /* private mode */ }
  const params = new URLSearchParams(location.search);
  applyLang(params.get("lang") === "en" || (!params.get("lang") && saved === "en") ? "en" : "fa");
  loadHealth();
})();
