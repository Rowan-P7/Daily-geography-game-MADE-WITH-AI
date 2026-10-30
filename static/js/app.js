(() => {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const views = ["home", "game", "results", "stats"];
  const state = {
    view: "home",
    game: null,
    selectedAnswer: null,
    question: null,
    result: null,
    selectedCountries: new Set(),
    sound: localStorage.getItem("atlas-sound") !== "off",
    countdownTimer: null,
    roundTimer: null,
    toastTimer: null,
  };

  async function api(path, options = {}) {
    const response = await fetch(path, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Something went wrong. Please try again.");
    return data;
  }

  function showToast(message) {
    const toast = $("#toast");
    toast.textContent = message;
    toast.classList.add("visible");
    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(() => toast.classList.remove("visible"), 2600);
  }

  function setView(name) {
    if (!views.includes(name)) return;
    state.view = name;
    for (const view of views) $(`#${view}-view`).classList.toggle("hidden", view !== name);
    document.querySelectorAll(".nav-link").forEach((link) => {
      link.classList.toggle("active", link.dataset.view === name || (name === "results" && link.dataset.view === "home"));
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
    if (name === "stats") loadStats();
  }

  function renderHome(data) {
    const date = new Date(`${data.date}T00:00:00Z`);
    $("#today-date").textContent = date.toLocaleDateString(undefined, {
      weekday: "long", month: "long", day: "numeric", timeZone: "UTC",
    }).toUpperCase();
    $("#home-streak").textContent = data.stats.current_streak;
    $("#header-streak").textContent = data.stats.current_streak;
    $("#home-games").textContent = data.stats.games_played;
    $("#home-best").textContent = data.stats.best_score ? data.stats.best_score.toLocaleString() : "—";
    const button = $("#play-button");
    const status = $("#daily-status-text");
    if (data.completed) {
      button.innerHTML = 'Review today&#39;s results <span aria-hidden="true">↗</span>';
      status.textContent = "Today's challenge complete. See how you did.";
      $("#status-icon").textContent = "✓";
    } else if (data.in_progress) {
      button.innerHTML = 'Continue today&#39;s challenge <span aria-hidden="true">↗</span>';
      status.textContent = "Your challenge is saved. Pick up where you left off.";
      $("#status-icon").textContent = "◷";
    } else {
      button.innerHTML = 'Play today&#39;s challenge <span aria-hidden="true">↗</span>';
      status.textContent = "Today's challenge is ready when you are.";
      $("#status-icon").textContent = "◎";
    }
    updateCountdown(data.seconds_until_reset);
  }

  function updateCountdown(seconds) {
    clearInterval(state.countdownTimer);
    let remaining = Math.max(0, seconds);
    const render = () => {
      const hours = Math.floor(remaining / 3600);
      const minutes = Math.floor((remaining % 3600) / 60);
      const secs = remaining % 60;
      $("#countdown").textContent = `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
      if (remaining > 0) remaining -= 1;
    };
    render();
    state.countdownTimer = setInterval(render, 1000);
  }

  function playSound(correct) {
    if (!state.sound) return;
    try {
      const context = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      oscillator.type = "sine";
      oscillator.frequency.value = correct ? 620 : 230;
      gain.gain.setValueAtTime(0.06, context.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + 0.18);
      oscillator.connect(gain);
      gain.connect(context.destination);
      oscillator.start();
      oscillator.stop(context.currentTime + 0.18);
      oscillator.onended = () => context.close();
    } catch (error) {
      console.warn("Sound playback is unavailable.", error);
    }
  }

  async function startGame(mode) {
    try {
      const game = await api("/api/games", {
        method: "POST",
        body: JSON.stringify({ mode }),
      });
      if (game.status === "complete") {
        state.result = game.result;
        renderResults(game.result);
        setView("results");
        return;
      }
      state.game = game;
      $("#game-mode-label").textContent = mode === "daily" ? "TODAY'S MINI-GAME CIRCUIT" : "PRACTICE FIELD NOTES";
      $("#leave-game").textContent = mode === "daily" ? "← Back to today" : "← Leave practice";
      $("#feedback").classList.add("hidden");
      $("#submit-button").classList.remove("hidden");
      $("#next-button").classList.add("hidden");
      $("#submit-button").disabled = true;
      $("#game-score").textContent = game.score.toLocaleString();
      if (game.round) renderMiniRound(game);
      else renderQuestion(game);
      setView("game");
    } catch (error) {
      showToast(error.message);
    }
  }

  async function loadMiniGames() {
    try {
      const { games } = await api("/api/minigames");
      const select = $("#practice-type");
      select.replaceChildren();
      games.forEach((game) => {
        const option = makeElement("option", "", game.name);
        option.value = game.id;
        select.append(option);
      });
    } catch (error) {
      showToast(error.message);
    }
  }

  function renderQuestion(game) {
    state.game = game;
    state.question = game.question;
    state.selectedAnswer = null;
    $("#round-stage").classList.add("hidden");
    $("#question-media").classList.toggle("hidden", !game.question.media);
    $("#answer-options").classList.remove("hidden");
    $("#question-hint").textContent = "Choose one answer · correct answers are worth 1,000 points plus a speed bonus";
    $("#question-category").textContent = game.question.category.toUpperCase();
    $("#question-difficulty").textContent = game.question.difficulty.toUpperCase();
    $("#question-difficulty").dataset.level = game.question.difficulty;
    $("#question-number").textContent = `${String(game.question_index + 1).padStart(2, "0")} / ${String(game.question_count).padStart(2, "0")}`;
    $("#progress-bar").style.width = `${(game.question_index / game.question_count) * 100}%`;
    $("#question-text").textContent = game.question.question;
    const media = $("#question-media");
    media.classList.toggle("hidden", !game.question.media);
    media.replaceChildren();
    if (game.question.media?.type === "flag") {
      media.textContent = game.question.media.value;
      media.setAttribute("aria-label", `Flag of ${game.question.question}`);
    } else if (game.question.media?.type === "map") {
      renderCoordinateMap(media, game.question.media.value);
    }
    const options = $("#answer-options");
    options.replaceChildren();
    if (game.question.answer_type === "number") {
      const label = document.createElement("label");
      label.className = "answer-option estimate-option";
      label.htmlFor = "estimate-input";
      const marker = document.createElement("span");
      marker.className = "option-key";
      marker.textContent = "≈";
      const input = document.createElement("input");
      input.id = "estimate-input";
      input.type = "number";
      input.min = game.question.min_value;
      input.max = game.question.max_value;
      input.step = "any";
      input.placeholder = `${game.question.min_value.toLocaleString()} – ${game.question.max_value.toLocaleString()}`;
      input.setAttribute("aria-label", `Your estimate in ${game.question.unit}`);
      const unit = document.createElement("span");
      unit.className = "estimate-unit";
      unit.textContent = game.question.unit;
      label.append(marker, input, unit);
      options.append(label);
      input.addEventListener("input", () => {
        state.selectedAnswer = input.value === "" ? null : Number(input.value);
        $("#submit-button").disabled = state.selectedAnswer === null || !input.checkValidity();
      });
    } else {
      game.question.options.forEach((answer, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "answer-option";
        button.setAttribute("aria-pressed", "false");
        const key = document.createElement("span");
        key.className = "option-key";
        key.textContent = index + 1;
        const label = document.createElement("span");
        label.textContent = answer;
        button.append(key, label);
        button.addEventListener("click", () => selectAnswer(answer));
        options.append(button);
      });
    }
    $("#feedback").classList.add("hidden");
    $("#submit-button").classList.remove("hidden");
    $("#next-button").classList.add("hidden");
    $("#submit-button").disabled = true;
    $("#game-score").textContent = game.score.toLocaleString();
  }

  function makeElement(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function renderMiniRound(game) {
    state.game = game;
    state.round = game.round;
    state.question = game.round;
    state.selectedAnswer = null;
    const round = game.round;
    const payload = round.payload;
    const stage = $("#round-stage");
    stage.replaceChildren();
    stage.classList.remove("hidden", "revealed");
    $("#question-media").classList.add("hidden");
    $("#answer-options").classList.add("hidden");
    $("#question-category").textContent = round.game_name.toUpperCase();
    $("#question-difficulty").textContent = round.difficulty.toUpperCase();
    $("#question-difficulty").dataset.level = round.difficulty;
    $("#question-number").textContent = `${String(game.question_index + 1).padStart(2, "0")} / ${String(game.question_count).padStart(2, "0")}`;
    $("#progress-bar").style.width = `${(game.question_index / game.question_count) * 100}%`;
    $("#question-text").textContent = round.prompt;
    $("#question-hint").textContent = `${round.game_name} · ${round.difficulty} · up to 1,100 points + combo`;
    $("#game-score").textContent = game.score.toLocaleString();
    $("#submit-button").classList.remove("hidden");
    $("#next-button").classList.add("hidden");
    $("#submit-button").disabled = true;
    $("#feedback").classList.add("hidden");
    $("#report-button").dataset.questionId = round.id;
    $("#report-button").classList.remove("hidden");

    if (round.game_type === "mystery_country") {
      const clue = makeElement("div", "round-hint", `CLUE ${payload.clues_revealed} / ${payload.clue_count} · ${payload.clue}`);
      const reveal = makeElement("button", "hint-button", payload.clues_revealed < payload.clue_count ? "Reveal next clue" : "All clues revealed");
      reveal.type = "button";
      reveal.disabled = payload.clues_revealed >= payload.clue_count;
      reveal.addEventListener("click", revealHint);
      clue.append(reveal);
      stage.append(clue);
      const form = makeElement("div", "guess-form");
      const input = makeElement("input");
      input.type = "text";
      input.autocomplete = "off";
      input.placeholder = "Name the country…";
      input.setAttribute("aria-label", "Mystery country guess");
      input.addEventListener("input", () => {
        state.selectedAnswer = input.value.trim() || null;
        $("#submit-button").disabled = !state.selectedAnswer;
      });
      form.append(input);
      stage.append(form, makeElement("p", "mini-count", `${payload.guesses_remaining} guesses left · solve sooner for more points`));
    } else if (round.game_type === "higher_lower") {
      const row = makeElement("div", "compare-row");
      [payload.left, payload.right].forEach((country, index) => {
        const card = makeElement("div", "compare-card");
        card.append(makeElement("span", "compare-flag", index === 0 ? payload.left_flag : payload.right_flag));
        card.append(makeElement("strong", "compare-name", country));
        const bar = makeElement("div", "compare-bar-track round-reveal");
        const fill = makeElement("span");
        fill.style.width = index === 0 ? "72%" : "55%";
        bar.append(fill);
        card.append(bar);
        const value = makeElement("span", "compare-value round-reveal");
        value.dataset.compareValue = index === 0 ? "left_value" : "right_value";
        card.append(value);
        row.append(card);
      });
      row.insertBefore(makeElement("div", "compare-vs", "VS"), row.children[1]);
      stage.append(row);
      const actions = makeElement("div", "compare-actions");
      [["left", `${payload.left} has more`], ["right", `${payload.right} has more`], ["tie", "They're equal"]].forEach(([value, label]) => {
        const button = makeElement("button", "compare-choice", label);
        button.type = "button";
        button.addEventListener("click", () => selectRoundAnswer(value, actions));
        actions.append(button);
      });
      stage.append(actions);
    } else if (round.game_type === "country_outline") {
      const frame = makeElement("div", "outline-frame");
      frame.append(makeElement("span", "photo-fallback", "Loading country outline…"));
      stage.append(frame);
      drawCountryOutline(frame, payload.outline_geometry).catch(showMapError);
      const input = makeElement("input", "round-text-input");
      input.type = "text";
      input.autocomplete = "off";
      input.placeholder = "Your answer…";
      input.setAttribute("aria-label", "Country outline guess");
      input.addEventListener("input", () => {
        state.selectedAnswer = input.value.trim() || null;
        $("#submit-button").disabled = !state.selectedAnswer;
      });
      stage.append(input);
    } else if (round.game_type === "closest_wins") {
      const control = makeElement("div", "estimate-control");
      const slider = makeElement("input");
      slider.type = "range";
      slider.min = payload.min_value;
      slider.max = payload.max_value;
      slider.value = Math.round((payload.min_value + payload.max_value) / 2);
      const number = makeElement("input");
      number.type = "number";
      number.min = payload.min_value;
      number.max = payload.max_value;
      number.step = "any";
      number.value = slider.value;
      number.setAttribute("aria-label", `Your estimate in ${payload.unit}`);
      const unit = makeElement("span", "estimate-unit", payload.unit);
      const sync = (value) => {
        number.value = value;
        slider.value = value;
        state.selectedAnswer = value === "" ? null : Number(value);
        $("#submit-button").disabled = state.selectedAnswer === null || !number.checkValidity();
      };
      slider.addEventListener("input", () => sync(slider.value));
      number.addEventListener("input", () => sync(number.value));
      control.append(slider, number, unit);
      stage.append(control);
      stage.append(makeElement("p", "mini-count", `Range: ${payload.min_value.toLocaleString()}–${payload.max_value.toLocaleString()} ${payload.unit}`));
    } else if (round.game_type === "flag_connections") {
      state.selectedCountries = new Set();
      stage.append(makeElement("p", "round-instruction", "Tap every flag that fits. Tap again to undo."));
      const grid = makeElement("div", "flag-grid");
      payload.flags.forEach((item) => {
        const button = makeElement("button", "flag-option");
        button.type = "button";
        button.setAttribute("aria-pressed", "false");
        button.append(makeElement("span", "", item.flag), makeElement("span", "", item.name));
        button.addEventListener("click", () => toggleCountry(item.name, button));
        grid.append(button);
      });
      stage.append(grid, makeElement("p", "mini-count", "Timed round · your time is running"));
      startRoundTimer(payload.timer_seconds || 40, stage);
    } else if (round.game_type === "where_in_world") {
      const frame = makeElement("div", "photo-frame");
      const image = makeElement("img", "landmark-photo");
      image.src = payload.photo_url;
      image.alt = `Geographical photograph of an unidentified landmark. Photo credit: ${payload.photo_credit}.`;
      image.loading = "lazy";
      image.addEventListener("error", () => {
        image.remove();
        frame.append(makeElement("div", "photo-fallback", "This photograph is unavailable right now. Use the geographical clue."));
      }, { once: true });
      frame.append(image);
      const credit = makeElement("div", "photo-credit");
      credit.append(makeElement("span", "", `Photo: ${payload.photo_credit}`));
      stage.append(frame, credit);
      const hintRow = makeElement("div", "round-hint", payload.hint || "No hint revealed yet.");
      const hintButton = makeElement("button", "hint-button", payload.hint_revealed ? "Hint used" : "Reveal a hint");
      hintButton.type = "button";
      hintButton.disabled = payload.hint_revealed;
      hintButton.addEventListener("click", revealHint);
      hintRow.append(hintButton);
      stage.append(hintRow);
      const input = makeElement("input", "round-text-input");
      input.type = "text";
      input.autocomplete = "off";
      input.placeholder = "Your answer…";
      input.setAttribute("aria-label", "Landmark location guess");
      input.addEventListener("input", () => {
        state.selectedAnswer = input.value.trim() || null;
        $("#submit-button").disabled = !state.selectedAnswer;
      });
      stage.append(input);
    } else if (round.game_type === "border_battle") {
      state.selectedCountries = new Set();
      stage.append(makeElement("p", "round-instruction", "Select every neighbouring country on the map or in the country list."));
      const frame = makeElement("div", "map-frame");
      frame.append(makeElement("div", "photo-fallback", "Loading Natural Earth boundaries…"));
      stage.append(frame);
      drawClickableMap(frame, payload).catch(showMapError);
      const options = makeElement("div", "map-options");
      payload.countries.forEach((country) => {
        const button = makeElement("button", "map-option", country);
        button.type = "button";
        button.setAttribute("aria-pressed", "false");
        button.addEventListener("click", () => toggleCountry(country, button));
        options.append(button);
      });
      stage.append(options);
    } else if (round.game_type === "geography_connections") {
      const grid = makeElement("div", "connection-grid");
      payload.items.forEach((item) => grid.append(makeElement("span", "connection-place", item)));
      const input = makeElement("input", "round-text-input");
      input.type = "text";
      input.autocomplete = "off";
      input.placeholder = "What connects these places?";
      input.setAttribute("aria-label", "Geography connection answer");
      input.addEventListener("input", () => {
        state.selectedAnswer = input.value.trim() || null;
        $("#submit-button").disabled = !state.selectedAnswer;
      });
      stage.append(makeElement("p", "round-instruction", "Four places. One geographic thread."), grid, input);
    }
  }

  function toggleCountry(country, button) {
    if (state.selectedCountries.has(country)) state.selectedCountries.delete(country);
    else state.selectedCountries.add(country);
    button.classList.toggle("selected", state.selectedCountries.has(country));
    button.setAttribute("aria-pressed", String(state.selectedCountries.has(country)));
    state.selectedAnswer = [...state.selectedCountries];
    $("#submit-button").disabled = state.selectedCountries.size === 0;
  }

  function selectRoundAnswer(answer, container) {
    state.selectedAnswer = answer;
    container.querySelectorAll(".compare-choice").forEach((button) => {
      button.classList.toggle("selected", (answer === "left" && button.textContent.includes(state.round.payload.left)) ||
        (answer === "right" && button.textContent.includes(state.round.payload.right)));
    });
    $("#submit-button").disabled = false;
  }

  async function revealHint() {
    if (!state.game) return;
    try {
      const response = await api(`/api/games/${state.game.id}/hint`, { method: "POST", body: "{}" });
      state.game.round = response.round;
      renderMiniRound(state.game);
      showToast(response.hints_remaining ? "A new clue is on the map." : "Last hint revealed.");
    } catch (error) {
      showToast(error.message);
    }
  }

  function geometryPaths(geometry, project) {
    const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
    return polygons.flatMap((polygon) => polygon.map((ring) => {
      const points = ring.map(([longitude, latitude]) => project(longitude, latitude));
      return `M${points.map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`).join("L")}Z`;
    }));
  }

  async function drawCountryOutline(frame, geometry) {
    if (!geometry) throw new Error("The country outline could not be loaded.");
    const coordinates = [];
    const collect = (geometry) => {
      const polys = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
      polys.forEach((polygon) => polygon.forEach((ring) => coordinates.push(...ring)));
    };
    collect(geometry);
    const xs = coordinates.map((point) => point[0]);
    const ys = coordinates.map((point) => point[1]);
    const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
    const width = Math.max(1, maxX - minX), height = Math.max(1, maxY - minY);
    const scale = Math.min(780 / width, 340 / height);
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 840 400");
    svg.classList.add("outline-svg");
    const project = (longitude, latitude) => [
      420 + (longitude - (minX + maxX) / 2) * scale,
      200 - (latitude - (minY + maxY) / 2) * scale,
    ];
    geometryPaths(geometry, project).forEach((pathValue) => {
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", pathValue);
      path.classList.add("outline-path");
      svg.append(path);
    });
    frame.replaceChildren(svg);
  }

  async function drawClickableMap(frame, payload) {
    const response = await fetch(`/api/games/${state.game.id}/map`);
    if (!response.ok) throw new Error("Natural Earth map data could not be loaded.");
    const data = await response.json();
    const features = data.features;
    if (!features.length) throw new Error("No matching country boundaries were found.");
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 1000 500");
    svg.setAttribute("aria-label", "Clickable Natural Earth country map");
    svg.classList.add("interactive-map");
    features.forEach((feature) => {
      const displayName = Object.entries(payload.geo_names).find(([, geo]) => geo === feature.properties.ADMIN)?.[0]
        || (feature.properties.ADMIN === payload.target_geo_name ? payload.country : null);
      const isTarget = displayName === payload.country;
      const isOption = displayName !== null && payload.countries.includes(displayName);
      const project = (longitude, latitude) => [
        (longitude + 180) * 1000 / 360,
        (90 - latitude) * 500 / 180,
      ];
      geometryPaths(feature.geometry, project).forEach((pathValue) => {
        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", pathValue);
        path.setAttribute("class", isTarget ? "interactive-country target" : isOption ? "interactive-country" : "map-land");
        if (isOption) path.dataset.country = displayName;
        path.setAttribute("tabindex", isOption && !isTarget ? "0" : "-1");
        path.setAttribute("role", isOption && !isTarget ? "button" : "img");
        path.setAttribute("aria-label", displayName || feature.properties.ADMIN);
        if (isOption && !isTarget) path.addEventListener("click", () => {
          const button = [...$("#round-stage").querySelectorAll(".map-option")]
            .find((option) => option.textContent === displayName);
          if (button) button.click();
        });
        svg.append(path);
      });
    });
    frame.replaceChildren(svg);
  }

  function showMapError(error) {
    console.error(error);
    showToast(error.message || "The map could not be loaded.");
  }

  function startRoundTimer(seconds, stage) {
    if (state.roundTimer) clearInterval(state.roundTimer);
    const timer = makeElement("p", "mini-count round-timer");
    stage.append(timer);
    let remaining = seconds;
    timer.textContent = `Time left: ${remaining}s`;
    state.roundTimer = setInterval(() => {
      if (!stage.isConnected || state.view !== "game") {
        clearInterval(state.roundTimer);
        state.roundTimer = null;
        return;
      }
      remaining -= 1;
      timer.textContent = `Time left: ${Math.max(remaining, 0)}s`;
      timer.classList.toggle("timer-warning", remaining <= 8);
      if (remaining <= 0) {
        clearInterval(state.roundTimer);
        state.roundTimer = null;
        state.selectedAnswer = [...state.selectedCountries];
        submitAnswer();
      }
    }, 1000);
  }

  function renderCoordinateMap(container, coordinates) {
    const svgNamespace = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNamespace, "svg");
    svg.setAttribute("viewBox", "0 0 640 300");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Schematic world map with a marked coordinate");
    svg.classList.add("coordinate-map");
    const background = document.createElementNS(svgNamespace, "rect");
    background.setAttribute("width", "640");
    background.setAttribute("height", "300");
    background.setAttribute("rx", "8");
    background.setAttribute("fill", "#17251e");
    svg.append(background);
    for (let latitude = -60; latitude <= 60; latitude += 30) {
      const y = 150 - latitude * 1.65;
      const line = document.createElementNS(svgNamespace, "line");
      line.setAttribute("x1", "25");
      line.setAttribute("x2", "615");
      line.setAttribute("y1", String(y));
      line.setAttribute("y2", String(y));
      line.setAttribute("class", latitude === 0 ? "map-equator" : "map-gridline");
      svg.append(line);
    }
    for (let longitude = -150; longitude <= 150; longitude += 30) {
      const x = 320 + longitude * 1.65;
      const line = document.createElementNS(svgNamespace, "line");
      line.setAttribute("x1", String(x));
      line.setAttribute("x2", String(x));
      line.setAttribute("y1", "20");
      line.setAttribute("y2", "280");
      line.setAttribute("class", "map-gridline");
      svg.append(line);
    }
    const landShapes = [
      "M72 71l27-19 34 8 21-12 44 14 22 22-18 17-28 3-13 30-24 8-7 36-19 6-17-23-18-8-13-34-18-14-4-20z",
      "M192 174l21-9 22 10 16 25-8 26-18 11-7 37-18-5-8-32-14-24 2-23z",
      "M280 71l24-16 31 8 19-12 45 14 24 21-7 17-35 0-22 15-17 1-3 27-16 15-21-5-9-24-15-14-6-20z",
      "M325 160l27-12 22 15 13 30-14 29-19 36-15-9-13-37-15-17z",
      "M436 183l30-7 32 10 12 21-23 13-27-4-20-15z",
      "M510 89l28-9 26 10 9 18-21 7-30-10z",
    ];
    landShapes.forEach((shape) => {
      const path = document.createElementNS(svgNamespace, "path");
      path.setAttribute("d", shape);
      path.setAttribute("class", "map-land");
      svg.append(path);
    });
    const x = 320 + coordinates.longitude * 1.65;
    const y = 150 - coordinates.latitude * 1.65;
    const ring = document.createElementNS(svgNamespace, "circle");
    ring.setAttribute("cx", String(x));
    ring.setAttribute("cy", String(y));
    ring.setAttribute("r", "11");
    ring.setAttribute("class", "map-marker-ring");
    svg.append(ring);
    const marker = document.createElementNS(svgNamespace, "circle");
    marker.setAttribute("cx", String(x));
    marker.setAttribute("cy", String(y));
    marker.setAttribute("r", "4");
    marker.setAttribute("class", "map-marker");
    svg.append(marker);
    const caption = document.createElement("span");
    caption.className = "map-caption";
    caption.textContent = "SCHEMATIC WORLD MAP · EQUATOR SHOWN";
    container.append(svg, caption);
  }

  function selectAnswer(answer) {
    if (!state.question) return;
    state.selectedAnswer = answer;
    document.querySelectorAll(".answer-option").forEach((button) => {
      const selected = button.lastElementChild.textContent === answer;
      button.classList.toggle("selected", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
    $("#submit-button").disabled = false;
  }

  async function submitAnswer() {
    if (!state.game || state.selectedAnswer === null) return;
    if (state.roundTimer) {
      clearInterval(state.roundTimer);
      state.roundTimer = null;
    }
    $("#submit-button").disabled = true;
    try {
      const response = await api(`/api/games/${state.game.id}/answer`, {
        method: "POST",
        body: JSON.stringify({
          question_index: state.game.question_index,
          answer: state.selectedAnswer,
        }),
      });
      if (response.round_complete === false) {
        state.game.round = response.round;
        renderMiniRound(state.game);
        showFeedback(response.feedback);
        showToast("Not quite — the next clue is unlocked.");
        return;
      }
      if (response.feedback.left_value !== undefined) {
        $("#round-stage").classList.add("revealed");
        document.querySelectorAll("[data-compare-value]").forEach((value) => {
          const number = response.feedback[value.dataset.compareValue];
          value.textContent = Number(number).toLocaleString();
        });
        const max = Math.max(response.feedback.left_value, response.feedback.right_value);
        document.querySelectorAll(".compare-bar-track span").forEach((bar, index) => {
          const value = index === 0 ? response.feedback.left_value : response.feedback.right_value;
          bar.style.width = `${Math.max(4, value / max * 100)}%`;
        });
      }
      const correctCountries = new Set(response.feedback.correct_countries || []);
      const selectedCountries = new Set(Array.isArray(state.selectedAnswer) ? state.selectedAnswer : []);
      document.querySelectorAll(".flag-option, .map-option").forEach((button) => {
        const country = button.classList.contains("flag-option")
          ? button.lastElementChild.textContent
          : button.textContent;
        button.disabled = true;
        if (correctCountries.has(country)) button.classList.add("correct");
        else if (selectedCountries.has(country)) button.classList.add("incorrect");
      });
      document.querySelectorAll(".interactive-country[data-country]").forEach((path) => {
        path.classList.toggle("correct", correctCountries.has(path.dataset.country));
        path.classList.toggle("incorrect", selectedCountries.has(path.dataset.country) && !correctCountries.has(path.dataset.country));
      });
      $("#round-stage").querySelectorAll("button, input").forEach((control) => {
        control.disabled = true;
      });
      showFeedback(response.feedback);
      document.querySelectorAll(".answer-option").forEach((button) => {
        const input = button.querySelector("input");
        if (input) input.disabled = true;
        else {
          button.disabled = true;
          const answer = button.lastElementChild.textContent;
          if (answer === response.feedback.correct_answer) button.classList.add("correct");
          else if (answer === state.selectedAnswer) button.classList.add("incorrect");
        }
      });
      playSound(response.feedback.is_correct);
      state.game.score = response.score;
      state.game.question_index = response.question_index;
      $("#game-score").textContent = response.score.toLocaleString();
      $("#progress-bar").style.width = `${(response.question_index / response.question_count) * 100}%`;
      $("#submit-button").classList.add("hidden");
      $("#next-button").classList.remove("hidden");
      $("#next-button").textContent = response.complete ? "See your results →" : "Continue →";
      if (response.complete) {
        state.result = response.result;
        $("#next-button").dataset.complete = "true";
      } else {
        state.game.round = response.round;
        state.question = response.round || response.question;
        $("#next-button").dataset.complete = "false";
      }
    } catch (error) {
      $("#submit-button").disabled = false;
      showToast(error.message);
    }
  }

  function showFeedback(result) {
    const feedback = $("#feedback");
    const isCorrect = result.is_correct ?? result.correct;
    feedback.classList.remove("hidden", "wrong");
    if (!isCorrect) feedback.classList.add("wrong");
    const title = makeElement("div", "feedback-title");
    let answerText = result.correct_answer_display;
    if (!answerText && Array.isArray(result.correct_countries)) answerText = result.correct_countries.join(", ");
    if (result.correct_display) answerText = result.correct_display;
    if (result.correct_answer !== undefined && typeof result.correct_answer !== "object") answerText = result.correct_answer;
    title.textContent = isCorrect
      ? `That's right. ${Number(result.points || 0).toLocaleString()} points earned.${result.combo_bonus ? ` +${result.combo_bonus} combo` : ""}`
      : `Keep exploring. ${answerText ? `Answer: ${answerText}.` : `${Number(result.points || 0).toLocaleString()} points for the matches.`}`;
    const explanation = makeElement("p", "", result.explanation || "");
    const scoreLine = makeElement("div", "points-earned");
    if (result.correct_value !== undefined) {
      const delta = Number(result.difference).toLocaleString(undefined, { maximumFractionDigits: 1 });
      scoreLine.textContent = `Answer: ${result.correct_display} · Your guess was ${delta} ${result.unit} away`;
    } else if (result.left_value !== undefined) {
      scoreLine.textContent = `${result.left}: ${Number(result.left_value).toLocaleString()} · ${result.right}: ${Number(result.right_value).toLocaleString()} ${result.unit}`;
    } else if (result.correct_selected !== undefined) {
      scoreLine.textContent = `${result.correct_selected} neighbour(s) found · ${result.incorrect_selected} incorrect selection(s)`;
    } else if (result.correct_countries) {
      scoreLine.textContent = `Correct flags: ${result.correct_countries.join(", ")}`;
    } else {
      scoreLine.textContent = `${Number(result.points || 0).toLocaleString()} points · ${Math.round(result.elapsed_seconds || 0)} seconds`;
    }
    feedback.replaceChildren(title, explanation, scoreLine);
    if (result.photo_source) {
      const source = makeElement("a", "photo-source-link", "View photo source and license");
      source.href = result.photo_source;
      source.target = "_blank";
      source.rel = "noopener noreferrer";
      feedback.append(source);
    }
  }

  function continueGame() {
    if ($("#next-button").dataset.complete === "true") {
      renderResults(state.result);
      setView("results");
      if (state.game.mode === "daily") loadHome();
      return;
    }
    if (state.game.round) renderMiniRound(state.game);
    else renderQuestion(state.game);
  }

  function renderResults(result) {
    state.result = result;
    const isDaily = Boolean(result.date);
    const resultDate = result.date || new Date().toISOString().slice(0, 10);
    $("#result-date").textContent = isDaily
      ? new Date(`${resultDate}T00:00:00Z`).toLocaleDateString(undefined, {
        weekday: "long", month: "long", day: "numeric", year: "numeric", timeZone: "UTC",
      }).toUpperCase()
      : "PRACTICE FIELD NOTES";
    $("#result-context").textContent = isDaily ? "TODAY'S SCORE" : "PRACTICE SCORE";
    $("#result-score").textContent = result.score.toLocaleString();
    $("#result-correct").textContent = `${result.correct} / ${result.total}`;
    $("#result-accuracy").textContent = `${result.accuracy}%`;
    const minutes = Math.floor(result.time_seconds / 60);
    $("#result-time").textContent = `${minutes}:${String(result.time_seconds % 60).padStart(2, "0")}`;
    $("#result-streak").textContent = result.streak === null ? "Practice" : `${result.streak} ${result.streak === 1 ? "day" : "days"}`;
    const grade = result.accuracy >= 90 ? "WORLD CLASS" : result.accuracy >= 70 ? "WELL TRAVELLED" : result.accuracy >= 50 ? "FINDING YOUR WAY" : "JUST GETTING STARTED";
    $("#result-grade").textContent = grade;
    $("#result-max").textContent = `/ ${(result.max_score || result.total * 1250).toLocaleString()} points`;
    $("#result-subtitle").textContent = result.accuracy >= 80
      ? "A fine bit of exploring. The world looks good on you."
      : "A little more of the world, tucked away.";
    const review = $("#answer-review");
    review.replaceChildren();
    result.answers.forEach((answer, index) => {
      const row = document.createElement("div");
      row.className = "review-row";
      const mark = document.createElement("span");
      mark.className = `review-mark${answer.is_correct ? "" : " wrong"}`;
      mark.textContent = answer.is_correct ? "✓" : "×";
      const content = document.createElement("div");
      const question = document.createElement("span");
      question.className = "review-question";
      question.textContent = `${String(index + 1).padStart(2, "0")} · ${answer.question}`;
      const given = document.createElement("span");
      given.className = "review-answer";
      if (answer.game_type) {
        const correct = answer.correct_answer_display
          || answer.correct_display
          || answer.correct_countries?.join(", ")
          || answer.correct_answer;
        given.textContent = answer.is_correct
          ? `${answer.game_type.replaceAll("_", " ")} · ${correct ?? "Solved"}`
          : `Answer: ${correct ?? "Review the explanation"}`;
      } else {
        given.textContent = answer.is_correct
          ? answer.correct_answer_display
          : `You chose ${answer.answer_display} · Answer: ${answer.correct_answer_display}`;
      }
      content.append(question, given);
      const points = document.createElement("span");
      points.className = "review-points";
      points.textContent = `+${answer.points.toLocaleString()}`;
      const combo = answer.combo_bonus ? ` · +${answer.combo_bonus} combo` : "";
      points.textContent += combo;
      row.append(mark, content, points);
      review.append(row);
    });
  }

  async function loadHome() {
    try {
      renderHome(await api("/api/daily"));
    } catch (error) {
      showToast(error.message);
    }
  }

  async function loadStats() {
    try {
      const [stats, leaderboard] = await Promise.all([
        api("/api/stats"),
        api(`/api/leaderboard?date=${new Date().toISOString().slice(0, 10)}`),
      ]);
      $("#stat-games").textContent = stats.games_played;
      $("#stat-average").textContent = stats.average_score.toLocaleString();
      $("#stat-best").textContent = stats.best_score.toLocaleString();
      $("#stat-accuracy").textContent = `${stats.accuracy}%`;
      $("#stat-streak").textContent = stats.current_streak;
      $("#stat-longest").textContent = `${stats.longest_streak} ${stats.longest_streak === 1 ? "day" : "days"}`;
      const calendar = $("#calendar");
      calendar.replaceChildren();
      const firstDate = new Date(`${stats.calendar[0].date}T00:00:00Z`);
      const offset = (firstDate.getUTCDay() + 6) % 7;
      for (let i = 0; i < offset; i += 1) {
        const blank = document.createElement("span");
        calendar.append(blank);
      }
      stats.calendar.forEach((day) => {
        const date = new Date(`${day.date}T00:00:00Z`);
        const cell = document.createElement("span");
        cell.className = `calendar-day${day.completed ? " completed" : ""}${day.date === new Date().toISOString().slice(0, 10) ? " today" : ""}`;
        cell.textContent = date.getUTCDate();
        cell.title = `${day.date}${day.completed ? " · completed" : ""}`;
        calendar.append(cell);
      });
      const history = $("#score-history");
      history.replaceChildren();
      const maxScore = Math.max(...stats.calendar.map((day) => day.score || 0), 1);
      stats.calendar.forEach((day) => {
        const bar = document.createElement("span");
        const score = day.score || 0;
        bar.className = score ? "played" : "";
        bar.style.height = `${score ? Math.max(4, (score / maxScore) * 62) : 2}px`;
        bar.title = `${day.date}: ${score ? `${score.toLocaleString()} points` : "not played"}`;
        bar.setAttribute("aria-label", bar.title);
        history.append(bar);
      });
      const board = $("#leaderboard");
      board.replaceChildren();
      if (leaderboard.entries.length === 0) {
        const empty = document.createElement("p");
        empty.className = "empty-leaderboard";
        empty.textContent = "Complete today's challenge to join the board.";
        board.append(empty);
      } else {
        leaderboard.entries.forEach((entry) => {
          const row = document.createElement("div");
          row.className = "leader-row";
          const rank = document.createElement("span");
          rank.textContent = String(entry.rank).padStart(2, "0");
          const name = document.createElement("span");
          name.textContent = `${entry.name} · ${entry.correct}/${entry.total}`;
          const score = document.createElement("strong");
          score.textContent = entry.score.toLocaleString();
          row.append(rank, name, score);
          board.append(row);
        });
      }
    } catch (error) {
      showToast(error.message);
    }
  }

  async function shareResult() {
    const result = state.result;
    const label = result.date
      ? `daily geography · ${result.date}`
      : `${result.game_types?.[0]?.replaceAll("_", " ") || "geography"} practice`;
    const text = `atlas. ${label}\n${result.score.toLocaleString()} points · ${result.correct}/${result.total} correct\n${result.answers.map((answer) => answer.is_correct ? "🟩" : "⬛").join("")}\nCan you beat my score?`;
    try {
      if (navigator.share) await navigator.share({ title: "My Atlas result", text });
      else {
        await navigator.clipboard.writeText(text);
        showToast("Your result is copied and ready to share.");
      }
    } catch (error) {
      if (error.name !== "AbortError") showToast("Couldn't share your result on this device.");
    }
  }

  async function sendReport(event) {
    event.preventDefault();
    if (!state.question) return;
    const message = $("#report-message").value.trim();
    try {
      const response = await api("/api/reports", {
        method: "POST",
        body: JSON.stringify({ question_id: state.question.id, message }),
      });
      $("#report-status").textContent = response.message;
      $("#report-message").value = "";
    } catch (error) {
      $("#report-status").textContent = error.message;
    }
  }

  document.addEventListener("click", (event) => {
    const nav = event.target.closest("[data-view]");
    if (nav) {
      event.preventDefault();
      setView(nav.dataset.view);
      if (nav.dataset.view === "home") loadHome();
    }
    const action = event.target.closest("[data-action]");
    if (action?.dataset.action === "practice") $("#practice-dialog").showModal();
    if (event.target.closest("#play-button")) startGame("daily");
    if (event.target.closest("#submit-button")) submitAnswer();
    if (event.target.closest("#next-button")) continueGame();
    if (event.target.closest("#leave-game")) {
      setView("home");
      loadHome();
    }
    if (event.target.closest("#share-button")) shareResult();
    if (event.target.closest("#help-button")) $("#help-dialog").showModal();
    if (event.target.closest("#report-button")) {
      $("#report-status").textContent = "";
      $("#report-button").classList.add("hidden");
      $("#report-dialog").showModal();
    }
    if (event.target.closest("[data-close-dialog]")) event.target.closest("dialog").close();
  });

  document.querySelectorAll("dialog").forEach((dialog) => {
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
  });

  document.addEventListener("keydown", (event) => {
    if (state.view !== "game" || !state.question || !$("#feedback").classList.contains("hidden")) return;
    if (/^[1-4]$/.test(event.key) && Array.isArray(state.question.options)) {
      const answer = state.question.options[Number(event.key) - 1];
      if (answer) selectAnswer(answer);
    } else if (event.key === "Enter" && !$("#submit-button").disabled) {
      submitAnswer();
    }
  });

  $("#report-form").addEventListener("submit", sendReport);
  $("#practice-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const gameType = $("#practice-type").value;
    const difficulty = $("#practice-difficulty").value;
    $("#practice-dialog").close();
    api("/api/games", {
      method: "POST",
      body: JSON.stringify({ mode: "practice", game_type: gameType, difficulty }),
    }).then((game) => {
      state.game = game;
      $("#game-mode-label").textContent = "PRACTICE FIELD NOTES";
      $("#leave-game").textContent = "← Leave practice";
      if (game.round) renderMiniRound(game);
      else renderQuestion(game);
      setView("game");
    }).catch((error) => showToast(error.message));
  });
  $("#sound-button").classList.toggle("sound-off", !state.sound);
  $("#sound-button").addEventListener("click", () => {
    state.sound = !state.sound;
    localStorage.setItem("atlas-sound", state.sound ? "on" : "off");
    $("#sound-button").setAttribute("aria-label", state.sound ? "Mute sound" : "Enable sound");
    showToast(state.sound ? "Sound effects on." : "Sound effects off.");
  });
  $("#sound-button").setAttribute("aria-label", state.sound ? "Mute sound" : "Enable sound");

  loadMiniGames();
  loadHome();
})();
