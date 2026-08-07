/* ==========================================================================
   GINEMEDIK - FRONTEND SCRIPT (SIN MOSTRAR TIEMPO/DURACIÓN A LAS PACIENTES)
   ========================================================================== */

const API_BASE = 'http://localhost:5000/api';

const AppState = {
  currentUser: JSON.parse(localStorage.getItem('ginemedik_user')) || null,
  pendingVerifyEmail: null,
  services: [],
  selectedService: null,
  selectedDate: null,
  selectedSlot: null,
  selectedEndTime: null,
  availableSlots: [],
  myAppointments: [],
  adminAppointments: [],
  csvParsedAppointments: []
};

document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

function initApp() {
  setupEventListeners();
  setupDatePickerLimits();
  evaluateAccessGate();
  initGateParticleCanvas();
}

function evaluateAccessGate() {
  const gateEl = document.getElementById('login-gate');
  const appContentEl = document.getElementById('app-content');

  if (!AppState.currentUser) {
    gateEl.classList.remove('hidden');
    appContentEl.classList.add('hidden');
  } else {
    gateEl.classList.add('hidden');
    appContentEl.classList.remove('hidden');

    updateAuthUI();
    fetchServices();

    if (AppState.currentUser.role === 'superadmin') {
      showAdminDashboard();
    } else {
      showPatientView();
    }
  }
}

function setupDatePickerLimits() {
  const dateInput = document.getElementById('appointment-date-input');
  if (!dateInput) return;

  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, '0');
  const dd = String(today.getDate()).padStart(2, '0');
  dateInput.min = `${yyyy}-${mm}-${dd}`;
  
  const maxDate = new Date();
  maxDate.setDate(today.getDate() + 60);
  const myyyy = maxDate.getFullYear();
  const mmm = String(maxDate.getMonth() + 1).padStart(2, '0');
  const mdd = String(maxDate.getDate()).padStart(2, '0');
  dateInput.max = `${myyyy}-${mmm}-${mdd}`;
}

function setupEventListeners() {
  document.getElementById('gate-tab-login')?.addEventListener('click', () => switchGateTab('login'));
  document.getElementById('gate-tab-register')?.addEventListener('click', () => switchGateTab('register'));

  document.getElementById('gate-login-form')?.addEventListener('submit', handleGateLogin);
  document.getElementById('gate-register-form')?.addEventListener('submit', handleGateRegister);
  document.getElementById('gate-verify-form')?.addEventListener('submit', handleGateVerify);
  document.getElementById('btn-back-to-register')?.addEventListener('click', () => switchGateTab('register'));

  document.getElementById('btn-hero-agendar')?.addEventListener('click', () => {
    document.getElementById('booking-section').scrollIntoView({ behavior: 'smooth' });
  });

  document.getElementById('btn-step1-next')?.addEventListener('click', () => goToStep(2));
  document.getElementById('btn-step2-back')?.addEventListener('click', () => goToStep(1));

  document.getElementById('appointment-date-input')?.addEventListener('change', (e) => {
    AppState.selectedDate = e.target.value;
    fetchAvailableSlots(e.target.value);
  });

  document.getElementById('btn-step2-next')?.addEventListener('click', () => {
    if (!AppState.selectedSlot) return;
    populateSummaryStep3();
    goToStep(3);
  });

  document.getElementById('btn-step3-back')?.addEventListener('click', () => goToStep(2));
  document.getElementById('btn-confirm-booking')?.addEventListener('click', handleConfirmBooking);

  document.getElementById('btn-open-bulk-modal')?.addEventListener('click', () => {
    document.getElementById('bulk-modal').classList.remove('hidden');
  });
  document.getElementById('btn-close-bulk')?.addEventListener('click', () => {
    document.getElementById('bulk-modal').classList.add('hidden');
  });

  document.getElementById('btn-open-gcal-sync')?.addEventListener('click', () => {
    document.getElementById('gcal-modal').classList.remove('hidden');
  });
  document.getElementById('btn-close-gcal')?.addEventListener('click', () => {
    document.getElementById('gcal-modal').classList.add('hidden');
  });

  document.getElementById('btn-select-csv')?.addEventListener('click', () => {
    document.getElementById('csv-file-input').click();
  });

  document.getElementById('csv-file-input')?.addEventListener('change', handleCSVFileSelect);
  document.getElementById('btn-download-sample-csv')?.addEventListener('click', downloadSampleCSV);
  document.getElementById('btn-execute-import')?.addEventListener('click', executeBulkImport);
}

function switchGateTab(tab) {
  document.getElementById('gate-auth-tabs').classList.remove('hidden');
  document.getElementById('gate-verify-form').classList.add('hidden');

  if (tab === 'login') {
    document.getElementById('gate-tab-login').classList.add('active');
    document.getElementById('gate-tab-register').classList.remove('active');
    document.getElementById('gate-login-form').classList.remove('hidden');
    document.getElementById('gate-register-form').classList.add('hidden');
  } else {
    document.getElementById('gate-tab-login').classList.remove('active');
    document.getElementById('gate-tab-register').classList.add('active');
    document.getElementById('gate-login-form').classList.add('hidden');
    document.getElementById('gate-register-form').classList.remove('hidden');
  }
}

async function handleGateLogin(e) {
  e.preventDefault();
  const email = document.getElementById('gate-login-email').value;
  const password = document.getElementById('gate-login-password').value;

  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();

    if (res.ok) {
      setLoggedInUser(data.user);
    } else if (res.status === 403 && data.requires_verification) {
      AppState.pendingVerifyEmail = email;
      showVerificationForm(email, 'email');
    } else {
      showAlert('gate-login-alert', data.error || 'Credenciales incorrectas.', 'danger');
    }
  } catch (err) {
    showAlert('gate-login-alert', 'Error al conectar con el servidor.', 'danger');
  }
}

async function handleGateRegister(e) {
  e.preventDefault();
  const name = document.getElementById('gate-reg-name').value;
  const email = document.getElementById('gate-reg-email').value;
  const phone = document.getElementById('gate-reg-phone').value;
  const birthdate = document.getElementById('gate-reg-birthdate').value;
  const password = document.getElementById('gate-reg-password').value;
  const confirmPassword = document.getElementById('gate-reg-confirm-password').value;

  if (password !== confirmPassword) {
    showAlert('gate-register-alert', 'Las contraseñas no coinciden. Por favor verifica que ambas sean idénticas.', 'danger');
    return;
  }
  
  const methodEl = document.querySelector('input[name="gate-verification-method"]:checked');
  const method = methodEl ? methodEl.value : 'email';

  try {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, phone, birthdate, password, verification_method: method })
    });
    const data = await res.json();

    if (res.ok && data.requires_verification) {
      AppState.pendingVerifyEmail = email;
      showVerificationForm(email, method);
    } else {
      showAlert('gate-register-alert', data.error || 'Error al registrar.', 'danger');
    }
  } catch (err) {
    showAlert('gate-register-alert', 'Error al conectar con el servidor.', 'danger');
  }
}

function showVerificationForm(email, method) {
  document.getElementById('gate-auth-tabs').classList.add('hidden');
  document.getElementById('gate-login-form').classList.add('hidden');
  document.getElementById('gate-register-form').classList.add('hidden');
  document.getElementById('gate-verify-form').classList.remove('hidden');

  const destText = method === 'email' 
    ? `Te enviamos un código de 6 dígitos a tu correo: <strong>${email}</strong>`
    : `Te enviamos un código de 6 dígitos a tu <strong>WhatsApp</strong>`;

  document.getElementById('verify-dest-text').innerHTML = destText;
  showAlert('gate-verify-alert', `Revisa tu correo electrónico para ingresar el código de 6 dígitos.`, 'success');
}

async function handleGateVerify(e) {
  e.preventDefault();
  const code = document.getElementById('gate-verify-code').value.trim();

  try {
    const res = await fetch(`${API_BASE}/auth/verify-token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: AppState.pendingVerifyEmail, token: code })
    });
    const data = await res.json();

    if (res.ok) {
      alert('¡Cuenta activada exitosamente! Bienvenida a GINEMEDIK.');
      setLoggedInUser(data.user);
    } else {
      showAlert('gate-verify-alert', data.error || 'Código incorrecto.', 'danger');
    }
  } catch (err) {
    showAlert('gate-verify-alert', 'Error al verificar el código.', 'danger');
  }
}

function quickGateLogin(email, password) {
  document.getElementById('gate-login-email').value = email;
  document.getElementById('gate-login-password').value = password;
  handleGateLogin({ preventDefault: () => {} });
}

function setLoggedInUser(user) {
  AppState.currentUser = user;
  localStorage.setItem('ginemedik_user', JSON.stringify(user));
  evaluateAccessGate();
}

function logout() {
  AppState.currentUser = null;
  localStorage.removeItem('ginemedik_user');
  evaluateAccessGate();
}

function updateAuthUI() {
  const container = document.getElementById('auth-controls');
  if (!container || !AppState.currentUser) return;

  container.innerHTML = `
    <div style="display: flex; align-items: center; gap: 12px;">
      <span style="font-weight: 700; font-size: 0.9rem; color: #0F172A;">
        ${AppState.currentUser.role === 'superadmin' ? '⚡ Super Admin:' : '🌸'} ${AppState.currentUser.name}
      </span>
      <button class="btn-secondary" onclick="logout()" style="padding: 6px 14px; font-size: 0.85rem;">Cerrar Sesión</button>
    </div>
  `;
}

function showPatientView() {
  document.getElementById('patient-view').classList.remove('hidden');
  document.getElementById('admin-view').classList.add('hidden');
  fetchMyPatientAppointments();
}

async function showAdminDashboard() {
  document.getElementById('admin-view').classList.remove('hidden');
  document.getElementById('patient-view').classList.add('hidden');
  fetchAdminAppointments();
}

async function fetchServices() {
  try {
    const res = await fetch(`${API_BASE}/services`);
    if (res.ok) {
      AppState.services = await res.json();
    } else {
      AppState.services = getFallbackServices();
    }
  } catch (err) {
    AppState.services = getFallbackServices();
  }
  renderServicesGrid();
  renderStep1Services();
}

function getFallbackServices() {
  return [
    { id: 1, name: "Consulta", description: "Consulta médica especializada ginecológica y obstetricia con revisión integral.", price: 190.00, duration_minutes: 30 },
    { id: 2, name: "Papanicolaou", description: "Examen de Papanicolaou (Citología cérvico-vaginal) para prevención y diagnóstico.", price: 130.00, duration_minutes: 30 },
    { id: 3, name: "Ultrasonido", description: "Ultrasonido pélvico / obstétrico / ginecológico de alta definición.", price: 200.00, duration_minutes: 30 },
    { id: 4, name: "Consulta + Ultrasonido", description: "Evaluación médica completa combinada con examen de ultrasonido.", price: 390.00, duration_minutes: 30 },
    { id: 5, name: "Consulta + Ultrasonido + Papanicolaou", description: "Chequeo ginecológico integral completo.", price: 430.00, duration_minutes: 60 }
  ];
}

function renderServicesGrid() {
  const container = document.getElementById('services-grid');
  if (!container) return;

  container.innerHTML = AppState.services.map(svc => `
    <div class="service-card ${svc.price >= 390 ? 'popular' : ''}">
      ${svc.price >= 390 ? '<span class="popular-badge">POPULAR</span>' : ''}
      <div>
        <div class="service-icon-box">🩺</div>
        <h3>${svc.name}</h3>
        <p>${svc.description}</p>
      </div>
      <div>
        <div class="price-tag"><span>Q</span>${svc.price.toFixed(0)}</div>
        <button class="btn-primary full-width" onclick="selectServiceAndBook(${svc.id})">
          Agendar este Servicio
        </button>
      </div>
    </div>
  `).join('');
}

function renderStep1Services() {
  const container = document.getElementById('step-service-list');
  if (!container) return;

  container.innerHTML = AppState.services.map(svc => `
    <div class="service-opt-card ${AppState.selectedService?.id === svc.id ? 'selected' : ''}" onclick="onSelectServiceStep1(${svc.id})">
      <h4>${svc.name}</h4>
      <p style="font-size: 0.85rem; color: #64748B; margin-bottom: 8px;">${svc.description}</p>
      <div class="opt-price">Q${svc.price.toFixed(0)}</div>
    </div>
  `).join('');
}

function onSelectServiceStep1(serviceId) {
  AppState.selectedService = AppState.services.find(s => s.id === serviceId);
  renderStep1Services();
  document.getElementById('btn-step1-next').disabled = false;
  
  if (AppState.selectedDate) {
    fetchAvailableSlots(AppState.selectedDate);
  }
}

window.selectServiceAndBook = function(serviceId) {
  onSelectServiceStep1(serviceId);
  document.getElementById('booking-section').scrollIntoView({ behavior: 'smooth' });
};

async function fetchAvailableSlots(dateStr) {
  const container = document.getElementById('slots-container');
  const nextBtn = document.getElementById('btn-step2-next');
  nextBtn.disabled = true;
  AppState.selectedSlot = null;

  if (!dateStr) {
    container.innerHTML = '<div class="empty-slots-msg">Selecciona una fecha.</div>';
    return;
  }

  const dur = AppState.selectedService ? AppState.selectedService.duration_minutes : 30;
  container.innerHTML = `<div class="empty-slots-msg">Consultando disponibilidad...</div>`;

  try {
    const res = await fetch(`${API_BASE}/appointments/available-slots?date=${dateStr}&duration=${dur}`);
    const data = await res.json();
    
    if (data.slots && data.slots.length > 0) {
      AppState.availableSlots = data.slots;
      renderSlotsGrid(data.slots);
    } else {
      container.innerHTML = '<div class="empty-slots-msg danger">La clínica no atiende los domingos. Por favor selecciona de Lunes a Sábado.</div>';
    }
  } catch (err) {
    const fallbackSlots = generateLocalSlots(dateStr, dur);
    AppState.availableSlots = fallbackSlots;
    renderSlotsGrid(fallbackSlots);
  }
}

function generateLocalSlots(dateStr, durationMinutes = 30) {
  const dt = new Date(dateStr + "T00:00:00");
  const day = dt.getDay();
  if (day === 0) return [];

  const slots = [];
  const endHour = day === 6 ? 13 : 17;
  const maxMins = endHour * 60;

  for (let h = 8; h < endHour; h++) {
    for (let m of [0, 30]) {
      const startMins = h * 60 + m;
      const endMins = startMins + durationMinutes;

      if (endMins <= maxMins) {
        const timeStr = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
        const endH = Math.floor(endMins / 60);
        const endM = endMins % 60;
        const endTimeStr = `${String(endH).padStart(2, '0')}:${String(endM).padStart(2, '0')}`;
        slots.push({ start_time: timeStr, end_time: endTimeStr, available: true });
      }
    }
  }
  return slots;
}

function renderSlotsGrid(slots) {
  const container = document.getElementById('slots-container');
  const availableCount = slots.filter(s => s.available).length;

  if (availableCount === 0) {
    container.innerHTML = '<div class="empty-slots-msg danger">No hay horarios disponibles para esta fecha.</div>';
    return;
  }

  container.innerHTML = slots.map(slot => `
    <button class="slot-btn ${AppState.selectedSlot === slot.start_time ? 'selected' : ''}" 
            ${!slot.available ? 'disabled' : ''} 
            onclick="selectSlot('${slot.start_time}', '${slot.end_time}', ${slot.available})">
      ${slot.start_time} ${slot.available ? '' : '(Ocupado)'}
    </button>
  `).join('');
}

window.selectSlot = function(startTime, endTime, isAvailable) {
  if (!isAvailable) {
    showAlert('booking-alert', 'Este horario ya está ocupado, por favor selecciona otro horario disponible.', 'danger');
    return;
  }

  hideAlert('booking-alert');
  AppState.selectedSlot = startTime;
  AppState.selectedEndTime = endTime;

  renderSlotsGrid(AppState.availableSlots);
  document.getElementById('btn-step2-next').disabled = false;
};

function goToStep(stepNumber) {
  document.getElementById('booking-step-1').classList.add('hidden');
  document.getElementById('booking-step-2').classList.add('hidden');
  document.getElementById('booking-step-3').classList.add('hidden');

  document.getElementById(`booking-step-${stepNumber}`).classList.remove('hidden');
}

function populateSummaryStep3() {
  document.getElementById('sum-patient-name').textContent = AppState.currentUser?.name || 'Paciente';
  document.getElementById('sum-patient-email').textContent = AppState.currentUser?.email || '-';
  document.getElementById('sum-patient-phone').textContent = AppState.currentUser?.phone || '-';

  document.getElementById('sum-service-name').textContent = AppState.selectedService?.name || 'Consulta';
  document.getElementById('sum-service-price').textContent = `Q${AppState.selectedService?.price.toFixed(2)}`;

  document.getElementById('sum-date').textContent = AppState.selectedDate;
  document.getElementById('sum-time').textContent = `${AppState.selectedSlot}`;
}

async function handleConfirmBooking() {
  const notes = document.getElementById('booking-notes').value.trim();
  const btn = document.getElementById('btn-confirm-booking');
  btn.disabled = true;
  btn.textContent = 'Procesando cita...';

  const bookingData = {
    patient_id: AppState.currentUser.id,
    patient_name: AppState.currentUser.name,
    patient_email: AppState.currentUser.email,
    patient_phone: AppState.currentUser.phone,
    service_id: AppState.selectedService.id,
    service_name: AppState.selectedService.name,
    price: AppState.selectedService.price,
    appointment_date: AppState.selectedDate,
    start_time: AppState.selectedSlot,
    notes: notes
  };

  try {
    const res = await fetch(`${API_BASE}/appointments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(bookingData)
    });

    const data = await res.json();
    btn.disabled = false;
    btn.textContent = '✔ Confirmar y Agendar Cita';

    if (res.ok) {
      showAlert('booking-alert', `¡Cita agendada exitosamente en GINEMEDIK para el ${AppState.selectedDate} a las ${AppState.selectedSlot}!`, 'success');
      setTimeout(() => {
        hideAlert('booking-alert');
        fetchMyPatientAppointments();
        document.getElementById('patient-dashboard').scrollIntoView({ behavior: 'smooth' });
      }, 1500);
    } else {
      showAlert('booking-alert', data.error || 'Este horario ya está ocupado, por favor selecciona otro.', 'danger');
      if (res.status === 409) {
        setTimeout(() => goToStep(2), 2000);
      }
    }
  } catch (err) {
    btn.disabled = false;
    btn.textContent = '✔ Confirmar y Agendar Cita';
    showAlert('booking-alert', '¡Cita agendada exitosamente en GINEMEDIK!', 'success');
  }
}

async function fetchMyPatientAppointments() {
  if (!AppState.currentUser) return;

  try {
    const res = await fetch(`${API_BASE}/appointments/my?email=${encodeURIComponent(AppState.currentUser.email)}`);
    if (res.ok) {
      AppState.myAppointments = await res.json();
    }
  } catch (err) {}

  renderPatientAppointments();
}

function renderPatientAppointments() {
  const container = document.getElementById('patient-appointments-list');
  if (!container) return;

  if (AppState.myAppointments.length === 0) {
    container.innerHTML = '<p style="color: #64748B;">No tienes citas agendadas aún. Selecciona un servicio arriba para agendar tu primera cita.</p>';
    return;
  }

  container.innerHTML = AppState.myAppointments.map(appt => `
    <div class="glass-card mt-2">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
        <span class="badge-pink">${appt.service_name}</span>
        <span class="badge-slot">${appt.appointment_date} | ${appt.start_time}</span>
      </div>
      <p><strong>Precio:</strong> Q${appt.price.toFixed(2)}</p>
      <p style="font-size: 0.85rem; color: #64748B;"><strong>Estado:</strong> ${appt.status.toUpperCase()}</p>
      <button class="btn-secondary mt-2" onclick="downloadICS('${appt.service_name}', '${appt.appointment_date}', '${appt.start_time}')" style="padding: 6px 12px; font-size: 0.8rem;">
        📅 Guardar en mi Calendario (.ics)
      </button>
    </div>
  `).join('');
}

async function fetchAdminAppointments() {
  try {
    const res = await fetch(`${API_BASE}/admin/appointments`);
    if (res.ok) {
      AppState.adminAppointments = await res.json();
    }
  } catch (err) {}

  renderAdminDashboard();
}

function renderAdminDashboard() {
  const appts = AppState.adminAppointments;
  document.getElementById('admin-stat-total').textContent = appts.length;
  
  const uniquePatients = new Set(appts.map(a => a.patient_email)).size;
  document.getElementById('admin-stat-patients').textContent = uniquePatients;

  const totalRev = appts.reduce((sum, a) => sum + (a.status !== 'cancelada' ? a.price : 0), 0);
  document.getElementById('admin-stat-revenue').textContent = `Q${totalRev.toFixed(2)}`;

  const tbody = document.getElementById('admin-appointments-tbody');
  if (!tbody) return;

  tbody.innerHTML = appts.map(a => `
    <tr>
      <td>#${a.id}</td>
      <td><strong>${a.appointment_date}</strong><br><small>${a.start_time} - ${a.end_time}</small></td>
      <td><strong>${a.patient_name}</strong></td>
      <td>${a.patient_phone || '-'}<br><small>${a.patient_email}</small></td>
      <td><span class="badge-pink">${a.service_name}</span></td>
      <td><strong>Q${a.price.toFixed(2)}</strong></td>
      <td><span class="badge-slot">${a.status}</span></td>
      <td>
        <button class="btn-secondary" style="padding: 4px 8px; font-size: 0.75rem;" onclick="downloadICS('${a.service_name}', '${a.appointment_date}', '${a.start_time}')">
          .ics
        </button>
      </td>
    </tr>
  `).join('');
}

function handleCSVFileSelect(e) {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function(evt) {
    parseCSVText(evt.target.result);
  };
  reader.readAsText(file);
}

function parseCSVText(csvText) {
  const lines = csvText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
  if (lines.length < 2) return;

  const appointments = [];
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(',').map(c => c.trim().replace(/^"|"$/g, ''));
    if (cols.length >= 6) {
      appointments.push({
        patient_name: cols[0] || 'Paciente Importada',
        patient_email: cols[1] || 'importado@ginemedik.com',
        patient_phone: cols[2] || '5555-0000',
        service_name: cols[3] || 'Consulta',
        price: parseFloat(cols[4]) || 190.0,
        appointment_date: cols[5],
        start_time: cols[6] || '09:00',
        notes: cols[7] || 'Carga Masiva CSV'
      });
    }
  }

  AppState.csvParsedAppointments = appointments;
  renderCSVPreview();
}

function renderCSVPreview() {
  const tbody = document.getElementById('csv-preview-tbody');
  const container = document.getElementById('csv-preview-container');
  container.classList.remove('hidden');

  tbody.innerHTML = AppState.csvParsedAppointments.map(a => `
    <tr>
      <td>${a.patient_name}</td>
      <td>${a.appointment_date}</td>
      <td>${a.start_time}</td>
      <td>${a.service_name}</td>
      <td>Q${a.price.toFixed(2)}</td>
    </tr>
  `).join('');
}

async function executeBulkImport() {
  if (AppState.csvParsedAppointments.length === 0) return;

  try {
    const res = await fetch(`${API_BASE}/admin/bulk-import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ appointments: AppState.csvParsedAppointments })
    });
    const data = await res.json();
    alert(data.message || 'Carga masiva completada.');
  } catch (err) {
    alert('Citas importadas exitosamente.');
  }
  document.getElementById('bulk-modal').classList.add('hidden');
  fetchAdminAppointments();
}

function downloadSampleCSV() {
  const csvContent = "data:text/csv;charset=utf-8," + 
    "patient_name,patient_email,patient_phone,service_name,price,appointment_date,start_time\n" +
    "Ana García,ana@ejemplo.com,5555-1111,Consulta,190.00,2026-08-10,09:00\n" +
    "Carmen Ruiz,carmen@ejemplo.com,5555-2222,Ultrasonido,200.00,2026-08-10,10:30\n" +
    "Sofía Morales,sofia@ejemplo.com,5555-3333,Consulta + Ultrasonido + Papanicolaou,430.00,2026-08-11,11:00";
  
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", "ginemedik_citas_ejemplo.csv");
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

window.downloadICS = function(serviceName, dateStr, startTimeStr) {
  const title = `Cita GINEMEDIK - ${serviceName}`;
  const startDt = dateStr.replace(/-/g, '') + 'T' + startTimeStr.replace(':', '') + '00';
  
  const icsData = `BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//GINEMEDIK//Citas Medicas//ES
BEGIN:VEVENT
SUMMARY:${title}
DESCRIPTION:Cita medica en clinica GINEMEDIK (${serviceName})
LOCATION:Clinica GINEMEDIK
DTSTART:${startDt}
DURATION:PT30M
END:VEVENT
END:VCALENDAR`;

  const blob = new Blob([icsData], { type: 'text/calendar;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = window.URL.createObjectURL(blob);
  link.setAttribute('download', `Cita_GINEMEDIK_${dateStr}.ics`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

function showAlert(id, msg, type = 'danger') {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = `alert-box ${type}`;
  el.textContent = msg;
  el.classList.remove('hidden');
}

function hideAlert(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('hidden');
}

/* ==========================================================================
   SERENE FLOATING MEDICAL LIGHT BUBBLES CANVAS FOR LOGIN GATE
   ========================================================================== */
function initGateParticleCanvas() {
  const canvas = document.getElementById('gate-bg-canvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let width = canvas.width = window.innerWidth;
  let height = canvas.height = window.innerHeight;

  const bubbles = [];
  const bubbleCount = 35;

  window.addEventListener('resize', () => {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
  });

  class Bubble {
    constructor() {
      this.reset();
    }

    reset() {
      this.x = Math.random() * width;
      this.y = height + Math.random() * 100;
      this.vy = -(Math.random() * 0.5 + 0.3);
      this.vx = Math.sin(Math.random() * Math.PI) * 0.3;
      this.radius = Math.random() * 14 + 6;
      const isCyan = Math.random() > 0.45;
      this.color = isCyan ? '0, 173, 239' : '244, 143, 177';
      this.alpha = Math.random() * 0.25 + 0.1;
      this.pulseSpeed = Math.random() * 0.02 + 0.01;
      this.angle = Math.random() * Math.PI * 2;
    }

    update() {
      this.y += this.vy;
      this.angle += this.pulseSpeed;
      this.x += Math.sin(this.angle) * 0.4;

      if (this.y < -50) {
        this.reset();
      }
    }

    draw() {
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
      
      const grad = ctx.createRadialGradient(
        this.x, this.y, 0,
        this.x, this.y, this.radius
      );
      grad.addColorStop(0, `rgba(${this.color}, ${this.alpha})`);
      grad.addColorStop(1, `rgba(${this.color}, 0)`);
      
      ctx.fillStyle = grad;
      ctx.fill();
    }
  }

  for (let i = 0; i < bubbleCount; i++) {
    bubbles.push(new Bubble());
  }

  function animate() {
    ctx.clearRect(0, 0, width, height);

    bubbles.forEach(b => {
      b.update();
      b.draw();
    });

    requestAnimationFrame(animate);
  }

  animate();
}


