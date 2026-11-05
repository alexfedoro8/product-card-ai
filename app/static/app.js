"use strict";

// ---------- утилиты ----------
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

/** Создаёт элемент; строки вставляются как текст (никакого innerHTML с данными). */
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function toast(text) {
  const box = $("#toast");
  box.textContent = text;
  box.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (box.hidden = true), 1800);
}

async function copy(text, label = "Скопировано") {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const area = el("textarea", {}, text);
    document.body.append(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  }
  toast(label);
}

function download(filename, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = el("a", { href: url, download: filename });
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function slug(text) {
  return (text || "card").toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "-").replace(/^-|-$/g, "").slice(0, 60);
}

// ---------- панель ввода ----------
const form = $("#product-form");
const jsonInput = $("#json-input");
// form.name — это атрибут самой формы, поэтому поля берём через elements.
const field = (name) => form.elements.namedItem(name);
let inputMode = "form";

function addSpecRow(name = "", value = "") {
  const row = el(
    "div",
    { class: "spec-row" },
    el("input", { placeholder: "название", value: name, "aria-label": "Название характеристики" }),
    el("input", { placeholder: "значение", value: value, "aria-label": "Значение" }),
    el("button", { type: "button", class: "icon-btn", title: "Удалить", onclick: () => row.remove() }, "×"),
  );
  $("#specs").append(row);
  return row;
}

function formToObject() {
  const specs = {};
  for (const row of $$("#specs .spec-row")) {
    const [nameInput, valueInput] = row.querySelectorAll("input");
    const name = nameInput.value.trim();
    if (name) specs[name] = valueInput.value.trim();
  }
  const images = imageLines();
  return {
    name: field("name").value.trim(),
    manufacturer: field("manufacturer").value.trim() || null,
    category: field("category").value.trim() || null,
    specs,
    description: field("description").value.trim() || null,
    images,
  };
}

function objectToForm(data) {
  field("name").value = data.name ?? "";
  field("manufacturer").value = data.manufacturer ?? "";
  field("category").value = data.category ?? "";
  field("description").value = data.description ?? "";
  field("images").value = (data.images ?? []).join("\n");
  $("#specs").replaceChildren();
  const specs = data.specs ?? {};
  for (const [name, value] of Object.entries(specs)) addSpecRow(name, value ?? "");
  if (!Object.keys(specs).length) addSpecRow();
  renderPhotoPreviews();
}

function setInputMode(mode) {
  hideInputError();
  if (mode === inputMode) return;
  if (mode === "json") {
    jsonInput.value = JSON.stringify(formToObject(), null, 2);
  } else {
    try {
      objectToForm(JSON.parse(jsonInput.value || "{}"));
    } catch (err) {
      showInputError(`JSON не разобран, форма не обновлена: ${err.message}`);
      return;
    }
  }
  inputMode = mode;
  $$("[data-input-tab]").forEach((b) => b.classList.toggle("active", b.dataset.inputTab === mode));
  $$("[data-input-view]").forEach((v) => (v.hidden = v.dataset.inputView !== mode));
}

function showInputError(text) {
  const box = $("#input-error");
  box.textContent = text;
  box.hidden = false;
}
function hideInputError() {
  $("#input-error").hidden = true;
}

// ---------- фото ----------
function imageLines() {
  return field("images").value.split("\n").map((s) => s.trim()).filter(Boolean);
}

function renderPhotoPreviews() {
  $("#photo-previews").replaceChildren(
    ...imageLines().map((url) =>
      el("div", { class: "thumb" },
        el("img", { src: url, alt: "", referrerpolicy: "no-referrer" }),
        el("button", { type: "button", title: "Убрать фото", onclick: () => removePhoto(url) }, "×"),
      ),
    ),
  );
}

function removePhoto(url) {
  field("images").value = imageLines().filter((u) => u !== url).join("\n");
  renderPhotoPreviews();
}

async function uploadPhotos(files) {
  hideInputError();
  const button = $("#upload-btn");
  button.disabled = true;
  button.textContent = "Загрузка…";
  try {
    for (const file of files) {
      const response = await fetch("/api/v1/images", {
        method: "POST",
        headers: { "Content-Type": file.type || "application/octet-stream" },
        body: file,
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        showInputError(`${file.name}: ${payload.message || "не удалось загрузить"}`);
        continue;
      }
      field("images").value = [...imageLines(), payload.url].join("\n");
    }
  } catch {
    showInputError("Сервер недоступен — фото не загружено.");
  } finally {
    button.disabled = false;
    button.textContent = "Загрузить фото";
    renderPhotoPreviews();
  }
}

// ---------- отправка ----------
const views = { empty: "#output-empty", loading: "#output-loading", error: "#output-error", result: "#output-result" };
function showView(name) {
  for (const [key, sel] of Object.entries(views)) $(sel).hidden = key !== name;
  $("#output-tabs").hidden = name !== "result";
}

let lastCard = null;

async function submit(event) {
  event.preventDefault();
  hideInputError();

  let body;
  if (inputMode === "json") {
    body = jsonInput.value; // как есть — ошибки JSON проверяет сервер
  } else {
    const data = formToObject();
    if (!data.name) return showInputError("Укажите название товара.");
    body = JSON.stringify(data);
  }

  const button = $("#submit");
  button.disabled = true;
  showView("loading");
  try {
    const response = await fetch("/api/v1/cards", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    const payload = await response.json().catch(() => ({ message: `Сервер ответил ${response.status}` }));
    if (!response.ok) return showError(payload);
    lastCard = payload;
    renderResult(payload);
    showView("result");
  } catch (err) {
    showError({ message: "Сервер недоступен. Проверьте, что приложение запущено.", details: [String(err)] });
  } finally {
    button.disabled = false;
  }
}

function showError(payload) {
  const box = $("#output-error");
  const details = payload.details ?? [];
  // replaceChildren превращает null в текст «null», поэтому список добавляем только если он есть
  box.replaceChildren(el("b", {}, payload.message || "Ошибка"));
  if (details.length) box.append(el("ul", {}, details.map((d) => el("li", {}, d))));
  showView("error");
}

// ---------- панель вывода ----------
function sectionHead(title, copyText) {
  return el(
    "div",
    { class: "sec-head" },
    el("h3", {}, title),
    copyText ? el("button", { type: "button", class: "copy", onclick: () => copy(copyText) }, "Копировать") : null,
  );
}

function renderGallery(card) {
  if (!card.images.length) {
    return el("div", { class: "gallery" }, el("div", { class: "no-photo" }, el("b", {}, "Фото нет"), "запросить у производителя"));
  }
  const main = el("img", { src: card.images[0], alt: card.name, referrerpolicy: "no-referrer" });
  const wrap = el("div", {}, el("div", { class: "gallery" }, main));
  if (card.images.length > 1) {
    wrap.append(
      el("div", { class: "thumbs" },
        card.images.map((src) => el("img", { src, alt: "", referrerpolicy: "no-referrer", onclick: () => (main.src = src) })),
      ),
    );
  }
  return wrap;
}

/** Абзацы описания; строки, начинающиеся с «- », — маркированный список. */
function renderDescription(text) {
  const nodes = [];
  for (const block of text.split(/\n\s*\n/)) {
    let list = null;
    let para = [];
    const flushPara = () => {
      if (para.length) nodes.push(el("p", {}, para.join(" ")));
      para = [];
    };
    for (const raw of block.split("\n")) {
      const line = raw.trim();
      if (!line) continue;
      if (line.startsWith("- ")) {
        flushPara();
        if (!list) {
          list = el("ul", { class: "desc-list" });
          nodes.push(list);
        }
        list.append(el("li", {}, line.slice(2)));
      } else {
        list = null;
        para.push(line);
      }
    }
    flushPara();
  }
  return nodes;
}

function renderCard(card) {
  const fromDescription = (row) =>
    row.source === "описание" ? el("span", { class: "src", title: `Цитата из описания: «${row.quote}»` }, "из описания") : null;

  const gapRows = card.missing_fields.filter(
    (m) => m.name !== "Фото товара" && m.name !== "Текстовое описание / паспорт",
  );

  const quick = el(
    "dl",
    { class: "quick-specs" },
    card.key_specs.slice(0, 6).map((row) => el("div", {}, el("dt", {}, row.name), el("dd", {}, row.value))),
  );
  const heroSide = el("div", {}, quick);

  const paragraphs = renderDescription(card.seo_description);

  const table = el(
    "table",
    { class: "spec-table" },
    el("tbody", {},
      card.key_specs.map((row) => el("tr", {}, el("td", {}, row.name), el("td", {}, row.value, fromDescription(row)))),
      gapRows.map((m) => el("tr", { class: "nodata" }, el("td", {}, m.name), el("td", {}, "данных нет"))),
    ),
  );
  const specsText = [
    ...card.key_specs.map((r) => `${r.name}: ${r.value}`),
    ...gapRows.map((m) => `${m.name}: данных нет`),
  ].join("\n");

  return [
    renderQuality(card),
    el("div", { class: "crumbs" }, ["Каталог", card.category || card.meta.device_type].join(" / ")),
    el("div", { class: "sec-head", style: "border:0;padding:0;margin:0" },
      el("h1", {}, card.seo_title),
      el("button", { type: "button", class: "copy", onclick: () => copy(card.seo_title) }, "Копировать"),
    ),
    el("div", { class: "byline" }, card.manufacturer ? `Производитель: ${card.manufacturer}` : "Производитель: данных нет"),
    el("div", { class: "hero" }, renderGallery(card), heroSide),

    el("section", { class: "sec" }, sectionHead("Описание", card.seo_description), paragraphs),
    el("section", { class: "sec" }, sectionHead("Характеристики", specsText), table),

    card.missing_fields.length
      ? el("section", { class: "sec gaps" },
          el("h3", {}, "Требует уточнения у поставщика"),
          el("ul", {}, card.missing_fields.map((m) => el("li", {}, el("b", {}, m.name), ` — ${m.reason}`))),
        )
      : null,

    el("section", { class: "sec manager" },
      el("div", { class: "tag" }, "Для менеджера · не публикуется"),
      el("div", { class: "sec-head", style: "border:0;padding:0;margin:0 0 6px" },
        el("h3", { style: "text-transform:none;letter-spacing:0" }, "Кому подходит и какие задачи решает"),
        el("button", { type: "button", class: "copy", onclick: () => copy(card.commercial_block) }, "Копировать"),
      ),
      el("p", {}, card.commercial_block),
    ),

    el("section", { class: "sec" },
      sectionHead("Поисковые запросы", card.search_queries.join("\n")),
      el("div", { class: "chips" }, card.search_queries.map((q) => el("span", { class: "chip" }, q))),
    ),

    el("div", { class: "meta-line" },
      `Тип: ${card.meta.device_type} · Модель: ${card.meta.model} · Попыток генерации: ${card.meta.attempts}`,
    ),
  ];
}

const QUALITY_ICON = { good: "✓", gaps: "!", poor: "i" };

/** Блок «Оценка введённых данных» — первое, что видит пользователь после генерации. */
function renderQuality(card) {
  const q = card.data_quality;
  const requirements = el(
    "ul",
    { class: "requirements" },
    q.requirements.map((r) =>
      el("li", { class: r.ok ? "req ok" : "req no" },
        el("span", { class: "req-mark", "aria-hidden": "true" }, r.ok ? "✓" : "✗"),
        el("span", { class: "req-name" }, r.name),
        el("span", { class: "req-value" }, r.value),
        r.hint ? el("span", { class: "req-hint" }, r.hint) : null,
      ),
    ),
  );

  return el("section", { class: `quality q-${q.level}` },
    el("div", { class: "quality-head" },
      el("span", { class: "quality-icon", "aria-hidden": "true" }, QUALITY_ICON[q.level]),
      el("div", {},
        el("div", { class: "quality-tag" }, "Оценка введённых данных"),
        el("div", { class: "quality-label" }, q.label),
      ),
    ),
    requirements,
    q.how_to_improve.length
      ? el("div", { class: "improve" },
          el("b", {}, "Как улучшить карточку"),
          el("ul", {}, q.how_to_improve.map((tip) => el("li", {}, tip))),
        )
      : null,
    card.warnings.length
      ? el("div", { class: "warns" },
          el("b", {}, "Проверка текста: модель не устранила замечания — проверьте вручную"),
          el("ul", {}, card.warnings.map((w) => el("li", {}, w))))
      : null,
  );
}

function renderResult(card) {
  $("#card").replaceChildren(...renderCard(card).filter(Boolean));
  $("#markdown-view").textContent = card.markdown;
  $("#json-view").textContent = JSON.stringify(card, null, 2);
  setOutputTab("card");
}

function setOutputTab(tab) {
  $$("[data-output-tab]").forEach((b) => b.classList.toggle("active", b.dataset.outputTab === tab));
  $$("[data-output-view]").forEach((v) => (v.hidden = v.dataset.outputView !== tab));
}

const actions = {
  "copy-md": () => copy(lastCard.markdown, "Markdown скопирован"),
  "download-md": () => download(`${slug(lastCard.name)}.md`, lastCard.markdown, "text/markdown;charset=utf-8"),
  "download-json": () =>
    download(`${slug(lastCard.name)}.json`, JSON.stringify(lastCard, null, 2), "application/json;charset=utf-8"),
  print: () => {
    setOutputTab("card");
    window.print();
  },
};

// ---------- запуск ----------
$$("[data-input-tab]").forEach((b) => b.addEventListener("click", () => setInputMode(b.dataset.inputTab)));
$$("[data-output-tab]").forEach((b) => b.addEventListener("click", () => setOutputTab(b.dataset.outputTab)));
$$("[data-action]").forEach((b) => b.addEventListener("click", () => lastCard && actions[b.dataset.action]()));
$("#add-spec").addEventListener("click", () => addSpecRow().querySelector("input").focus());
$("#clear").addEventListener("click", () => {
  objectToForm({});
  jsonInput.value = "";
  hideInputError();
});
form.addEventListener("submit", submit);
$("#upload-btn").addEventListener("click", () => $("#photo-file").click());
$("#photo-file").addEventListener("change", (event) => {
  uploadPhotos([...event.target.files]);
  event.target.value = "";
});
field("images").addEventListener("input", renderPhotoPreviews);

addSpecRow();
