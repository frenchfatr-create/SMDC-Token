
(() => {
  const tg = window.Telegram?.WebApp;

  tg?.ready();
  tg?.expand();

  const $ = (id) => document.getElementById(id);

  const views = ["home", "listings", "profile", "admin", "form"];

  const initData = tg?.initData || "";

  let submitting = false;

  // -----------------------------
  // УВЕДОМЛЕНИЯ
  // -----------------------------

  function toast(message) {
    const el = $("toast");

    if (!el) {
      console.log(message);
      return;
    }

    el.textContent = message;
    el.classList.add("show");

    setTimeout(() => {
      el.classList.remove("show");
    }, 3500);
  }

  // -----------------------------
  // API ЗАПРОСЫ
  // -----------------------------

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
      throw new Error(
        data.error || `Ошибка сервера: ${response.status}`
      );
    }

    return data;
  }

  // -----------------------------
  // ПЕРЕКЛЮЧЕНИЕ ЭКРАНОВ
  // -----------------------------

  function showView(name) {
    views.forEach(view => {
      $(view + "View")?.classList.toggle(
        "hidden",
        view !== name
      );
    });

    document.querySelectorAll(".tab").forEach(tab => {
      tab.classList.toggle(
        "active",
        tab.dataset.view === name
      );
    });
  }

  document.querySelectorAll(".tab").forEach(tab => {
    tab.addEventListener("click", () => {
      showView(tab.dataset.view);
    });
  });

  $("startListing")?.addEventListener("click", () => {
    showView("form");
  });

  $("newListing")?.addEventListener("click", () => {
    showView("form");
  });

  $("closeForm")?.addEventListener("click", () => {
    showView("home");
  });

  // -----------------------------
  // ПРОФИЛЬ TELEGRAM
  // -----------------------------

  const user = tg?.initDataUnsafe?.user;

  if (user) {
    if ($("profileName")) {
      $("profileName").textContent =
        [user.first_name, user.last_name]
          .filter(Boolean)
          .join(" ") || "SMDC Seller";
    }

    if ($("profileId")) {
      $("profileId").textContent =
        "Telegram ID: " + user.id;
    }
  }

  // -----------------------------
  // ОТОБРАЖЕНИЕ ОБЪЯВЛЕНИЙ
  // -----------------------------

  function renderListings(items) {
    const box = $("listingList");

    if (!box) return;

    box.innerHTML = "";

    if (!Array.isArray(items) || items.length === 0) {
      box.className = "empty-state";
      box.textContent =
        "Пока нет опубликованных объявлений.";

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
      meta.textContent =
        `${item.price} ${item.currency}`;

      card.append(title, description, meta);

      box.appendChild(card);
    });
  }

  // -----------------------------
  // ЗАГРУЗКА КАТАЛОГА
  // -----------------------------

  async function loadListings() {
    try {
      const items = await api("/api/listings");

      renderListings(items);

      if ($("homeCount")) {
        $("homeCount").textContent = items.length;
      }

    } catch (error) {
      console.error("Ошибка загрузки объявлений:", error);
      toast("Ошибка каталога: " + error.message);
    }
  }

  // -----------------------------
  // ОЧЕРЕДЬ МОДЕРАЦИИ
  // -----------------------------

  async function loadAdminQueue() {
    try {
      const items = await api("/api/admin/queue");

      $("adminTab")?.classList.remove("hidden");

      const box = $("adminQueue");

      if (!box) return;

      box.innerHTML = "";

      if (!Array.isArray(items) || items.length === 0) {
        box.textContent =
          "Новых объявлений на проверке нет.";

        return;
      }

      items.forEach(item => {
        const card = document.createElement("article");
        card.className = "listing-card";

        const title = document.createElement("b");
        title.textContent = item.title;

        const description = document.createElement("p");
        description.textContent =
          item.description || "Без описания";

        const meta = document.createElement("small");

        meta.textContent =
          `${item.price} ${item.currency} · Telegram ID: ${item.user_id}`;

        const approve = document.createElement("button");

        approve.textContent = "Одобрить";

        approve.addEventListener("click", () => {
          moderate(item.id, "approved");
        });

        const reject = document.createElement("button");

        reject.textContent = "Отклонить";

        reject.addEventListener("click", () => {
          moderate(item.id, "rejected");
        });

        card.append(
          title,
          description,
          meta,
          approve,
          reject
        );

        box.appendChild(card);
      });

    } catch (error) {
      $("adminTab")?.classList.add("hidden");

      console.error(
        "Ошибка загрузки админки:",
        error
      );

      toast("Ошибка админки: " + error.message);
    }
  }

  // -----------------------------
  // МОДЕРАЦИЯ ОБЪЯВЛЕНИЙ
  // -----------------------------

  async function moderate(id, status) {
    try {
      await api(
        `/api/admin/listings/${id}/moderate`,
        {
          method: "POST",
          body: JSON.stringify({
            status: status
          })
        }
      );

      if (status === "approved") {
        toast("Объявление опубликовано!");
      } else {
        toast("Объявление отклонено.");
      }

      await loadAdminQueue();
      await loadListings();

    } catch (error) {
      console.error("Ошибка модерации:", error);
      toast("Не удалось выполнить модерацию: " + error.message);
    }
  }

  // -----------------------------
  // СОЗДАНИЕ ОБЪЯВЛЕНИЯ
  // -----------------------------

  $("listingForm")?.addEventListener(
    "submit",
    async event => {
      event.preventDefault();

      if (submitting) return;

      if (!initData) {
        toast("Открой Mini App через Telegram.");
        return;
      }

      const form = event.currentTarget;

      const data = Object.fromEntries(
        new FormData(form).entries()
      );

      const title = String(data.title || "").trim();
      const description =
        String(data.description || "").trim();

      const price = Number(data.price);
      const currency = String(data.currency || "₽");

      if (!title) {
        toast("Введите название объявления.");
        return;
      }

      if (!Number.isFinite(price) || price <= 0) {
        toast("Введите корректную цену.");
        return;
      }

      submitting = true;

      const submitButton = form.querySelector(
        'button[type="submit"], input[type="submit"]'
      );

      if (submitButton) {
        submitButton.disabled = true;
      }

      try {
        const result = await api("/api/listings", {
          method: "POST",

          body: JSON.stringify({
            title: title,
            description: description,
            price: price,
            currency: currency
          })
        });

        if (!result.success) {
          throw new Error(
            result.error || "Сервер не подтвердил создание."
          );
        }

        form.reset();

        toast(
          `Объявление №${result.id} отправлено на проверку!`
        );

        showView("listings");

        await loadListings();
        await loadAdminQueue();

      } catch (error) {
        console.error(
          "Ошибка отправки объявления:",
          error
        );

        toast("Не удалось отправить: " + error.message);

      } finally {
        submitting = false;

        if (submitButton) {
          submitButton.disabled = false;
        }
      }
    }
  );

  // -----------------------------
  // ЗАПУСК MINI APP
  // -----------------------------

  async function start() {
    if (!initData) {
      toast("Открой Mini App через Telegram.");
      return;
    }

    await loadListings();
    await loadAdminQueue();
  }

  start();

})();
