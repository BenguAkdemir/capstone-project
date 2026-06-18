/**
 * Hybrid Work Weekly Planner — manual entry, database sync
 */

const DAYS = [
  { key: "monday", label: "Mon" },
  { key: "tuesday", label: "Tue" },
  { key: "wednesday", label: "Wed" },
  { key: "thursday", label: "Thu" },
  { key: "friday", label: "Fri" },
];

const DAY_OPTIONS = DAYS.map((d) => `<option value="${d.key}">${d.label}</option>`).join("");

let lastResponse = null;

const $ = (id) => document.getElementById(id);

// ——— Sekmeler ———
function switchTab(name) {
  document.querySelectorAll(".tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.tab === name);
  });
  document.querySelectorAll(".panel-view").forEach((p) => {
    p.classList.toggle("active", p.id === `panel-${name}`);
  });
}

// ——— Çalışan satırları ———
function nextEmpId() {
  const rows = document.querySelectorAll("#empInputTable tbody tr");
  return `E${String(rows.length + 1).padStart(3, "0")}`;
}

function addEmployeeRow(data = {}, skipRefresh = false) {
  const tbody = $("empInputTable").querySelector("tbody");
  const tr = document.createElement("tr");
  tr.dataset.eid = data.employee_id || nextEmpId();
  tr.innerHTML = `
    <td><input type="text" class="inp-name" placeholder="Full name" value="${data.name || ""}" /></td>
    <td><input type="text" class="inp-dept" placeholder="Department" value="${data.department || ""}" /></td>
    <td><input type="number" class="inp-min" min="0" max="5" value="${data.min_days ?? 2}" /></td>
    <td><input type="number" class="inp-max" min="0" max="5" value="${data.max_days ?? 4}" /></td>
    <td><button type="button" class="btn-icon btn-remove-emp" title="Remove">×</button></td>
  `;
  tbody.appendChild(tr);
  tr.querySelector(".btn-remove-emp").addEventListener("click", () => {
    tr.remove();
    refreshMatrixTables();
  });
  tr.querySelectorAll("input").forEach((inp) => {
    inp.addEventListener("change", refreshMatrixTables);
    inp.addEventListener("blur", refreshMatrixTables);
  });
  if (!skipRefresh) refreshMatrixTables();
}

function getEmployeesFromForm() {
  const rows = document.querySelectorAll("#empInputTable tbody tr");
  const employees = [];
  rows.forEach((tr) => {
    const name = tr.querySelector(".inp-name").value.trim();
    const department = tr.querySelector(".inp-dept").value.trim();
    if (!name || !department) return;
    employees.push({
      employee_id: tr.dataset.eid,
      name,
      department,
      min_days: Number(tr.querySelector(".inp-min").value),
      max_days: Number(tr.querySelector(".inp-max").value),
    });
  });
  return employees;
}

// ——— Kapasite ———
function renderCapacityInputs() {
  const grid = $("capacityGrid");
  grid.innerHTML = DAYS.map(
    (d) => `
    <label class="cap-item">
      <span>${d.label}</span>
      <input type="number" data-day="${d.key}" min="1" max="50" value="4" />
    </label>`,
  ).join("");
}

// ——— Müsaitlik / tercih matrisleri ———
function refreshMatrixTables() {
  const availTb = $("availTable").querySelector("tbody");
  const prefTb = $("prefTable").querySelector("tbody");
  availTb.innerHTML = "";
  prefTb.innerHTML = "";

  document.querySelectorAll("#empInputTable tbody tr").forEach((tr) => {
    const name = tr.querySelector(".inp-name").value.trim() || "New employee";
    const department = tr.querySelector(".inp-dept").value.trim();
    if (!department) return;
    const emp = {
      employee_id: tr.dataset.eid,
      name,
      department,
    };
    const ar = document.createElement("tr");
    ar.dataset.eid = emp.employee_id;
    let availCells = `<td class="emp-name">${emp.name}</td>`;
    DAYS.forEach((d) => {
      availCells += `<td><label class="check-cell"><input type="checkbox" data-day="${d.key}" checked /><span>Available</span></label></td>`;
    });
    ar.innerHTML = availCells;
    availTb.appendChild(ar);

    const pr = document.createElement("tr");
    pr.dataset.eid = emp.employee_id;
    let prefCells = `<td class="emp-name">${emp.name}</td>`;
    DAYS.forEach((d) => {
      prefCells += `<td><select data-day="${d.key}" class="pref-select">
        <option value="none">—</option>
        <option value="prefer">Prefer</option>
        <option value="avoid">Avoid</option>
      </select></td>`;
    });
    pr.innerHTML = prefCells;
    prefTb.appendChild(pr);
  });

  // Departman listesi güncellensin diye işbirliği satırlarındaki select'leri yenile
  document.querySelectorAll("#collabTable tbody tr").forEach((tr) => {
    const sel = tr.querySelector(".collab-dept");
    const cur = sel.value;
    const depts = [...new Set(getEmployeesFromForm().map((e) => e.department))];
    sel.innerHTML = depts.map((d) => `<option value="${d}">${d}</option>`).join("");
    if (depts.includes(cur)) sel.value = cur;
  });
}

function buildAvailability() {
  const list = [];
  document.querySelectorAll("#availTable tbody tr").forEach((tr) => {
    const eid = tr.dataset.eid;
    tr.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
      list.push({
        employee_id: eid,
        day: cb.dataset.day,
        available: cb.checked ? 1 : 0,
      });
    });
  });
  return list;
}

function buildPreferences() {
  const list = [];
  document.querySelectorAll("#prefTable tbody tr").forEach((tr) => {
    const eid = tr.dataset.eid;
    tr.querySelectorAll(".pref-select").forEach((sel) => {
      const v = sel.value;
      if (v === "prefer") {
        list.push({ employee_id: eid, day: sel.dataset.day, preferred: 1, avoid: 0 });
      } else if (v === "avoid") {
        list.push({ employee_id: eid, day: sel.dataset.day, preferred: 0, avoid: 1 });
      }
    });
  });
  return list;
}

function buildCapacity() {
  return DAYS.map((d) => ({
    day: d.key,
    capacity: Number(document.querySelector(`#capacityGrid input[data-day="${d.key}"]`).value),
  }));
}

// ——— İşbirliği ———
function addCollabRow(data = {}) {
  const tbody = $("collabTable").querySelector("tbody");
  const depts = [...new Set(getEmployeesFromForm().map((e) => e.department))];
  const deptOpts = depts.map((d) => `<option value="${d}" ${data.department === d ? "selected" : ""}>${d}</option>`).join("");
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td><select class="collab-dept">${deptOpts || '<option value="">—</option>'}</select></td>
    <td><select class="collab-day">${DAY_OPTIONS}</select></td>
    <td><input type="number" class="collab-min" min="1" max="20" value="${data.min_required ?? 2}" /></td>
    <td><button type="button" class="btn-icon btn-remove-collab">×</button></td>
  `;
  if (data.day) tr.querySelector(".collab-day").value = data.day;
  tbody.appendChild(tr);
  tr.querySelector(".btn-remove-collab").addEventListener("click", () => tr.remove());
}

function buildCollaboration() {
  const list = [];
  document.querySelectorAll("#collabTable tbody tr").forEach((tr) => {
    const department = tr.querySelector(".collab-dept").value;
    const day = tr.querySelector(".collab-day").value;
    const min_required = Number(tr.querySelector(".collab-min").value);
    if (department && day) list.push({ department, day, min_required });
  });
  return list;
}

function populateFormFromPayload(data) {
  $("empInputTable").querySelector("tbody").innerHTML = "";
  (data.employees || []).forEach((e) => addEmployeeRow(e, true));
  refreshMatrixTables();

  (data.capacity || []).forEach((c) => {
    const inp = document.querySelector(`#capacityGrid input[data-day="${c.day}"]`);
    if (inp) inp.value = c.capacity;
  });

  const availMap = {};
  (data.availability || []).forEach((a) => {
    availMap[`${a.employee_id}|${a.day}`] = a.available;
  });
  document.querySelectorAll("#availTable tbody tr").forEach((tr) => {
    const eid = tr.dataset.eid;
    tr.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
      const key = `${eid}|${cb.dataset.day}`;
      if (key in availMap) cb.checked = !!availMap[key];
    });
  });

  document.querySelectorAll("#prefTable tbody tr").forEach((tr) => {
    const eid = tr.dataset.eid;
    tr.querySelectorAll(".pref-select").forEach((sel) => {
      const pref = (data.preferences || []).find(
        (p) => p.employee_id === eid && p.day === sel.dataset.day,
      );
      if (!pref) {
        sel.value = "none";
        return;
      }
      if (pref.preferred) sel.value = "prefer";
      else if (pref.avoid) sel.value = "avoid";
      else sel.value = "none";
    });
  });

  $("collabTable").querySelector("tbody").innerHTML = "";
  (data.collaboration || []).forEach((c) => addCollabRow(c));

  if (data.weights) {
    $("wMiss").value = data.weights.w_miss;
    $("wIdle").value = data.weights.w_idle;
    $("wPref").value = data.weights.w_pref;
    $("lblMiss").textContent = sliderLabel(data.weights.w_miss, "miss");
    $("lblIdle").textContent = sliderLabel(data.weights.w_idle, "idle");
    $("lblPref").textContent = sliderLabel(data.weights.w_pref, "pref");
  }
}

async function loadPlanningFromDb() {
  try {
    const res = await fetch("/api/planning");
    if (!res.ok) return false;
    const data = await res.json();
    populateFormFromPayload(data);
    const badge = $("dbBadge");
    badge.classList.remove("hidden");
    badge.classList.add("visible", "ok");
    return true;
  } catch {
    return false;
  }
}

async function syncToDatabase(payload) {
  const res = await fetch("/api/employees/sync", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || data.error || "Failed to save to database");
  }
}

const FIELD_LABELS = {
  employees: "Employees",
  availability: "Availability",
  preferences: "Preferences",
  capacity: "Capacity",
  collaboration: "Collaboration",
};

function formatValidationIssues(issues) {
  return issues
    .map((i) => {
      const label = FIELD_LABELS[i.field] || i.field;
      return `[${label}] ${i.message}`;
    })
    .join("\n");
}

function formatInfeasibility(data) {
  const lines = [data.explanation || data.message || "No feasible schedule found."];
  (data.rules || []).forEach((rule) => lines.pusπh(`• ${rule}`));
  return lines.join("\n");
}

function validateBeforeSubmit(employees) {
  for (const e of employees) {
    if (e.min_days > e.max_days) {
      throw new Error(
        `${e.name}: minimum office days (${e.min_days}) cannot exceed maximum (${e.max_days}).`,
      );
    }
    if (e.min_days > 5 || e.max_days > 5) {
      throw new Error(`${e.name}: weekly office days cannot exceed 5.`);
    }
  }

  const deptCounts = {};
  employees.forEach((e) => {
    deptCounts[e.department] = (deptCounts[e.department] || 0) + 1;
  });

  const capacityByDay = Object.fromEntries(buildCapacity().map((c) => [c.day, c.capacity]));
  const collabByDay = {};

  document.querySelectorAll("#collabTable tbody tr").forEach((tr) => {
    const department = tr.querySelector(".collab-dept")?.value;
    const day = tr.querySelector(".collab-day")?.value;
    const min_required = Number(tr.querySelector(".collab-min")?.value || 0);
    if (!department || !day) return;
    const size = deptCounts[department] || 0;
    if (min_required > size) {
      const dayLabel = DAYS.find((d) => d.key === day)?.label || day;
      throw new Error(
        `Department "${department}" has ${size} employee(s); cannot require ${min_required} onsite on ${dayLabel}.`,
      );
    }
    const dayCap = capacityByDay[day];
    if (dayCap != null && min_required > dayCap) {
      const dayLabel = DAYS.find((d) => d.key === day)?.label || day;
      throw new Error(
        `Department "${department}" requires at least ${min_required} onsite on ${dayLabel}, but office capacity is only ${dayCap}.`,
      );
    }
    collabByDay[day] = (collabByDay[day] || 0) + min_required;
  });

  for (const [day, totalRequired] of Object.entries(collabByDay)) {
    const dayCap = capacityByDay[day];
    if (dayCap != null && totalRequired > dayCap) {
      const dayLabel = DAYS.find((d) => d.key === day)?.label || day;
      throw new Error(
        `On ${dayLabel}, department minimums total ${totalRequired}, which exceeds office capacity (${dayCap}).`,
      );
    }
  }

  for (const c of buildCapacity()) {
    if (c.capacity < 1) throw new Error("Office capacity must be at least 1.");
  }

  const avail = buildAvailability();
  for (const e of employees) {
    const availableDays = DAYS.filter((d) =>
      avail.some((a) => a.employee_id === e.employee_id && a.day === d.key && a.available),
    ).length;
    if (e.min_days > availableDays) {
      throw new Error(
        `${e.name}: minimum office days (${e.min_days}) exceeds available days (${availableDays}).`,
      );
    }
    if (e.max_days > availableDays) {
      throw new Error(
        `${e.name}: maximum office days (${e.max_days}) exceeds available days (${availableDays}).`,
      );
    }
  }
}

/** Same shape as backend SchedulingRequestDTO */
function buildPayload() {
  const employees = getEmployeesFromForm();
  if (!employees.length) throw new Error("Add at least one employee with name and department.");

  validateBeforeSubmit(employees);

  const availability = buildAvailability();
  if (availability.length !== employees.length * DAYS.length) {
    throw new Error(
      "Availability table is incomplete. Enter a department for each employee.",
    );
  }

  return {
    employees,
    availability,
    preferences: buildPreferences(),
    capacity: buildCapacity(),
    collaboration: buildCollaboration(),
    weights: {
      w_miss: Number($("wMiss").value),
      w_idle: Number($("wIdle").value),
      w_pref: Number($("wPref").value),
    },
  };
}

// ——— Sonuç: haftalık program tablosu ———
function renderSchedule(result) {
  const wrap = $("scheduleWrap");
  const empty = $("programEmpty");
  if (!result?.schedules?.length) {
    wrap.classList.add("hidden");
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");
  wrap.classList.remove("hidden");

  const tbody = $("scheduleTable").querySelector("tbody");
  tbody.innerHTML = "";
  const empMap = Object.fromEntries(getEmployeesFromForm().map((e) => [e.employee_id, e]));

  result.schedules.forEach((s) => {
    const emp = empMap[s.employee_id] || { name: s.employee_id, department: s.department };
    const tr = document.createElement("tr");
    let cells = `<td><strong>${emp.name}</strong></td><td>${s.department}</td>`;
    DAYS.forEach((d) => {
      const assigned = s.assigned_days?.[d.key];
      let cls = "remote";
      let text = "Remote";
      if (!isAvailCell(s.employee_id, d.key)) {
        cls = "unavailable";
        text = "—";
      } else if (assigned) {
        cls = "onsite";
        text = "Onsite";
        if (isPreferredCell(s.employee_id, d.key)) cls += " pref";
      }
      cells += `<td><span class="chip ${cls}">${text}</span></td>`;
    });
    cells += `<td class="total">${s.total_assigned}</td>`;
    tr.innerHTML = cells;
    tbody.appendChild(tr);
  });
}

function isAvailCell(eid, day) {
  const row = document.querySelector(`#availTable tr[data-eid="${eid}"]`);
  if (!row) return true;
  const cb = row.querySelector(`input[data-day="${day}"]`);
  return cb?.checked ?? true;
}

function isPreferredCell(eid, day) {
  const row = document.querySelector(`#prefTable tr[data-eid="${eid}"]`);
  if (!row) return false;
  const sel = row.querySelector(`select[data-day="${day}"]`);
  return sel?.value === "prefer";
}

function renderSummary(result) {
  if (!result) return;
  $("summaryCards").innerHTML = `
    <div class="stat"><span>Status</span><strong>${statusLabel(result.status)}</strong></div>
    <div class="stat"><span>Missing min. days</span><strong>${result.total_missing ?? 0}</strong></div>
    <div class="stat"><span>Idle capacity (week)</span><strong>${(result.day_summaries || []).reduce((s, d) => s + d.idle_capacity, 0).toFixed(0)} person-days</strong></div>
    <div class="stat"><span>Preference violations</span><strong>${result.total_preference_violations ?? 0}</strong></div>
    <div class="stat"><span>Avoid violations</span><strong>${result.total_avoid_violations ?? 0}</strong></div>
  `;

  const wl = $("warningsList");
  wl.innerHTML = "";
  if (result.infeasibility_explanation) {
    wl.innerHTML += `<li class="bad">${result.infeasibility_explanation}</li>`;
  }
  (result.warnings || []).forEach((w) => {
    const cls = w.code?.startsWith("infeasible") ? "bad" : "";
    wl.innerHTML += `<li class="${cls}">${w.message}</li>`;
  });
  if (!wl.children.length) {
    wl.innerHTML = `<li class="ok">No warnings — schedule looks consistent.</li>`;
  }

  const deptTb = $("deptTable").querySelector("tbody");
  deptTb.innerHTML = "";
  const collabMap = {};
  buildCollaboration().forEach((c) => {
    collabMap[`${c.department}|${c.day}`] = c.min_required;
  });
  (result.team_attendance || []).forEach((ta) => {
    const req = collabMap[`${ta.department}|${ta.day}`] ?? "—";
    const tr = document.createElement("tr");
    if (req !== "—" && ta.count < req) tr.className = "warn-row";
    const dayTr = DAYS.find((d) => d.key === ta.day);
    tr.innerHTML = `<td>${ta.department}</td><td>${dayTr?.label || ta.day}</td><td>${ta.count}</td><td>${req}</td>`;
    deptTb.appendChild(tr);
  });
}

function statusLabel(s) {
  const map = {
    optimal: "Success",
    partial: "Partial",
    infeasible: "Infeasible",
    timeout: "Timeout",
    error: "Error",
  };
  return map[s] || s;
}

function setStatus(result) {
  const b = $("statusBadge");
  if (!result) {
    b.textContent = "";
    b.className = "badge";
    return;
  }
  b.textContent = statusLabel(result.status);
  b.className = `badge visible ${result.status === "optimal" ? "ok" : "warn"}`;
  $("solveTime").textContent = result.solve_time_seconds
    ? `Solve: ${result.solve_time_seconds.toFixed(1)}s`
    : "";
}

function showError(msg) {
  const el = $("errorMsg");
  if (msg) {
    el.textContent = msg;
    el.style.whiteSpace = "pre-line";
    el.classList.add("visible");
  } else {
    el.textContent = "";
    el.style.whiteSpace = "";
    el.classList.remove("visible");
  }
}

// ——— Optimizasyon ———
async function optimize() {
  const btn = $("optimizeBtn");
  btn.disabled = true;
  showError(null);
  lastResponse = null;

  try {
    const payload = buildPayload();
    const res = await fetch("/api/optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      if (res.status === 422 && Array.isArray(data.issues)) {
        throw new Error(formatValidationIssues(data.issues));
      }
      if (res.status === 409) {
        const explanation = formatInfeasibility(data);
        lastResponse = { ...data, status: "infeasible" };
        setStatus(lastResponse);
        renderSchedule(null);
        renderSummary({
          status: "infeasible",
          infeasibility_explanation: data.explanation || data.message,
          warnings: (data.rules || []).map((rule) => ({
            code: "infeasible_rule",
            message: rule,
          })),
          day_summaries: [],
          team_attendance: [],
        });
        switchTab("summary");
        throw new Error(explanation);
      }
      throw new Error(
        data.message || data.explanation || data.error || `Error (${res.status})`,
      );
    }

    await syncToDatabase(payload);

    lastResponse = data;
    setStatus(data);
    renderSchedule(data);
    renderSummary(data);
    switchTab("schedule");
  } catch (e) {
    showError(e.message);
  } finally {
    btn.disabled = false;
  }
}

function sliderLabel(val, type) {
  if (type === "miss") return val >= 15 ? "very high" : val >= 8 ? "high" : "medium";
  if (type === "idle") return val >= 4 ? "high" : val >= 2 ? "medium" : "low";
  return val >= 6 ? "high" : val >= 3 ? "medium" : "low";
}

function bindSliders() {
  $("wMiss").addEventListener("input", (e) => {
    $("lblMiss").textContent = sliderLabel(Number(e.target.value), "miss");
  });
  $("wIdle").addEventListener("input", (e) => {
    $("lblIdle").textContent = sliderLabel(Number(e.target.value), "idle");
  });
  $("wPref").addEventListener("input", (e) => {
    $("lblPref").textContent = sliderLabel(Number(e.target.value), "pref");
  });
}

async function init() {
  renderCapacityInputs();
  bindSliders();

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
  });
  $("btnAddEmp").addEventListener("click", () => addEmployeeRow());
  $("btnAddCollab").addEventListener("click", () => addCollabRow());
  $("optimizeBtn").addEventListener("click", optimize);
  $("btnBackEdit").addEventListener("click", () => switchTab("input"));

  const loaded = await loadPlanningFromDb();
  if (!loaded) addEmployeeRow();
}

init();
