
(() => {
  const tg = window.Telegram?.WebApp;
  tg?.ready();
  tg?.expand();

  const $ = (id) => document.getElementById(id);
  const views = ["home", "listings", "profile", "admin", "form"];

  const initData = tg?.initData || "";

  async function api(path, options = {}) {
    const response = await fetch(path, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "X-Telegram-Init-Data": initData,
        ...(options.headers || {})
      }
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.error || "Ошибка сервера");
    }

    return data;
  }

  function toast(message) {
    const el = $("toast");
    if (!el) return;
    el.textContent = message;
    el.classList.add("show");
    setTimeout(() => el.classList.remove("show"), 2600);
  }

  function showView(name) {
    views.forEach(view => {
      $(view + "View")?.classList.toggle("hidden", view !== name);
    });

    document.querySelectorAll(".tab").forEach(tab => {
      tab.classList.toggle("active", tab.dataset.view === name);
    });
  }

  document.querySelectorAll(".tab").forEach(tab => {
    tab.addEventListener("click", () => showView(tab.dataset.view));
  });

  $("startListing")?.addEventListener("click", () => showView("form"));
  $("newListing")?.addEventListener("click", () => showView("form"));
  $("closeForm")?.addEventListener("click", () => showView("home"));

  const user = tg?.initDataUnsafe?.user;

  if (user) {
    $("profileName").textContent =
      [user.first_name, user.last_name].filter(Boolean).join(" ") ||
      "SMDC Seller";

    $("profileId").textContent = "Telegram ID: " + user.id;
  }

  function renderListings(items) {
    const box = $("listingList");
    if (!box) return;

    box.innerHTML = "";

    if (!items.length) {
      box.className = "empty-state";
      box.textContent = "Пока нет опубликованных объявлений.";
      return;
    }

    box.className = "";

    items.forEach(item => {
      const card = document.createElement("article");
      card.className = "listing-card";

      const title = document.createElement("b");
      title.textContent = item.title;

      const description = document.createElement("p");
      description.textContent = item.description || "";

      const meta = document.createElement("small");
      meta.textContent = `${item.price} ${item.currency}`;

      card.append(title, description, meta);
      box.appendChild(card);
    });
  }

  async function loadListings() {
    try {
      const items = await api("/api/listings");
      renderListings(items);

      if ($("homeCount")) {
        $("homeCount").textContent = items.length;
      }
    } catch (error) {
      toast(error.message);
    }
  }

  async function loadAdminQueue() {
    try {
      const items = await api("/api/admin/queue");

      $("adminTab")?.classList.remove("hidden");

      const box = $("adminQueue");
      if (!box) return;

      box.innerHTML = "";

      if (!items.length) {
        box.textContent = "Новых объявлений на проверке нет.";
        return;
      }

      items.forEach(item => {
        const card = document.createElement("article");
        card.className = "listing-card";

        const title = document.createElement("b");
        title.textContent = item.title;

        const description = document.createElement("p");
        description.textContent = item.description || "";

        const meta = document.createElement("small");
        meta.textContent =
          `${item.price} ${item.currency} · Telegram ID: ${item.user_id}`;

        const approve = document.createElement("button");
        approve.textContent = "Одобрить";
        approve.addEventListener("click", () =>
          moderate(item.id, "approved")
        );

        const reject = document.createElement("button");
        reject.textContent = "Отклонить";
        reject.addEventListener("click", () =>
          moderate(item.id, "rejected")
        );

        card.append(title, description, meta, approve, reject);
        box.appendChild(card);
      });
    } catch (error) {
      // Обычный пользователь не получит доступ к очереди.
      $("adminTab")?.classList.add("hidden");
    }
  }

  async function moderate(id, status) {
    try {
      await api(`/api/admin/listings/${id}/moderate`, {
        method: "POST",
        body: JSON.stringify({ status })
      });

      toast(status === "approved" ? "Объявление опубликовано" : "Объявление отклонено");
      await loadAdminQueue();
      await loadListings();
    } catch (error) {
      toast(error.message);
    }
  }

  $("listingForm")?.addEventListener("submit", async event => {
    event.preventDefault();

    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form).entries());

    try {
      const result = await api("/api/listings", {
        method: "POST",
        body: JSON.stringify({
          title: data.title,
          description: data.description || "",
          price: data.price,
          currency: data.currency
        })
      });

      form.reset();
      toast(result.message || "Отправлено на проверку");
      showView("listings");
      await loadListings();
    } catch (error) {
      toast(error.message);
    }
  });

  async function start() {
    if (!initData) {
      toast("Открой Mini App через Telegram");
      return;
    }

    await loadListings();
    await loadAdminQueue();
  }

  start();
})();
