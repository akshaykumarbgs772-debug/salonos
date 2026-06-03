// ============================================================
// SalonOS – Frontend Application
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
  initModals();
  initToast();
  initSidebarToggle();
});

// ============================================================
// MODALS
// ============================================================
function initModals() {
  document.querySelectorAll('[data-modal]').forEach(btn => {
    btn.addEventListener('click', function() {
      const modalId = this.dataset.modal;
      const modal = document.getElementById(modalId);
      if (modal) openModal(modal);
    });
  });

  document.querySelectorAll('.modal-overlay').forEach(modal => {
    modal.addEventListener('click', function(e) {
      if (e.target === this) closeModal(this);
    });
    modal.querySelectorAll('.modal-close').forEach(btn => {
      btn.addEventListener('click', () => closeModal(modal));
    });
  });

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-overlay.active').forEach(closeModal);
    }
  });
}

function openModal(modal) {
  modal.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeModal(modal) {
  modal.classList.remove('active');
  document.body.style.overflow = '';
}

// ============================================================
// TOAST NOTIFICATIONS
// ============================================================
function initToast() {
  const container = document.createElement('div');
  container.id = 'toast-container';
  container.style.cssText = `
    position: fixed; bottom: 20px; right: 20px; z-index: 9999;
    display: flex; flex-direction: column; gap: 8px;
  `;
  document.body.appendChild(container);
}

function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const colors = {
    success: '#10B981', error: '#EF4444', warning: '#F59E0B', info: '#3B82F6'
  };
  const icons = {
    success: '✓', error: '✕', warning: '⚠', info: 'ℹ'
  };

  const toast = document.createElement('div');
  toast.style.cssText = `
    background: white; border-radius: 10px; padding: 14px 18px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.15); display: flex;
    align-items: center; gap: 10px; font-size: 14px; font-weight: 500;
    border-left: 4px solid ${colors[type]};
    animation: slideIn 0.3s ease; max-width: 380px;
    font-family: 'Inter', sans-serif;
  `;
  toast.innerHTML = `<span style="color:${colors[type]};font-weight:700">${icons[type]}</span> ${message}`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ============================================================
// SIDEBAR TOGGLE (mobile)
// ============================================================
function initSidebarToggle() {
  const toggle = document.getElementById('sidebarToggle');
  const sidebar = document.querySelector('.sidebar');
  if (toggle && sidebar) {
    toggle.addEventListener('click', () => sidebar.classList.toggle('open'));
  }
}

// ============================================================
// FORM HELPERS
// ============================================================
function serializeForm(form) {
  const data = {};
  new FormData(form).forEach((value, key) => { data[key] = value; });
  return data;
}

async function apiPost(url, data) {
  const isForm = data instanceof FormData;
  const resp = await fetch(url, {
    method: 'POST',
    headers: isForm ? {} : { 'Content-Type': 'application/json' },
    body: isForm ? data : JSON.stringify(data),
  });
  const result = await resp.json();
  if (!resp.ok) throw new Error(result.detail || 'Request failed');
  return result;
}

// ============================================================
// INIT PAGE-SPECIFIC
// ============================================================
if (document.getElementById('dashboard-page')) initDashboard();
if (document.getElementById('payments-page')) initPayments();
if (document.getElementById('clients-page')) initClients();
if (document.getElementById('appointments-page')) initAppointments();
if (document.getElementById('calendar-page')) initCalendar();
if (document.getElementById('inventory-page')) initInventory();

// ============================================================
// DASHBOARD
// ============================================================
function initDashboard() {
  loadWeeklyChart();
}

function loadWeeklyChart() {
  const canvas = document.getElementById('weeklyChart');
  if (!canvas) return;

  const labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const dataElement = document.getElementById('weeklyData');
  if (!dataElement) return;

  try {
    const values = JSON.parse(dataElement.textContent || '[]');
    const maxVal = Math.max(...values, 1);

    const bars = canvas.querySelectorAll('.chart-bar');
    bars.forEach((bar, i) => {
      const height = (values[i] / maxVal) * 100;
      setTimeout(() => {
        bar.style.height = Math.max(height, 4) + '%';
      }, i * 60);
    });

    const labels_el = canvas.querySelectorAll('.chart-label');
    labels_el.forEach((el, i) => { el.textContent = labels[i]; });
  } catch(e) {}
}

// ============================================================
// PAYMENTS
// ============================================================
function initPayments() {
  const form = document.getElementById('paymentForm');
  if (!form) return;

  form.addEventListener('submit', async function(e) {
    e.preventDefault();
    const btn = this.querySelector('[type="submit"]');
    btn.disabled = true; btn.textContent = 'Processing...';

    const items = [];
    document.querySelectorAll('.payment-item').forEach(row => {
      items.push({
        item_type: row.dataset.type || 'service',
        item_name: row.querySelector('.item-name')?.value || '',
        quantity: parseInt(row.querySelector('.item-qty')?.value || 1),
        unit_price: parseFloat(row.querySelector('.item-price')?.value || 0),
        stylist_id: row.querySelector('.item-stylist')?.value || null,
      });
    });

    const tipSplits = [];
    document.querySelectorAll('.tip-split-row').forEach(row => {
      tipSplits.push({
        stylist_id: row.querySelector('.split-stylist')?.value,
        percentage: parseFloat(row.querySelector('.split-pct')?.value || 0),
      });
    });

    const data = {
      client_id: document.getElementById('payClientId')?.value,
      appointment_id: document.getElementById('payApptId')?.value || null,
      items: items,
      tip_amount: parseFloat(document.getElementById('tipAmount')?.value || 0),
      discount_amount: parseFloat(document.getElementById('discountAmount')?.value || 0),
      payment_method: document.getElementById('paymentMethod')?.value || 'cash',
      card_last_four: document.getElementById('cardLastFour')?.value || null,
      tip_split: tipSplits.length > 0 ? tipSplits : null,
    };

    try {
      const result = await apiPost('/api/payments/process', data);
      showToast(`Payment processed: ₹${result.transaction.total.toFixed(2)}`, 'success');
      setTimeout(() => location.reload(), 1000);
    } catch (err) {
      showToast(err.message, 'error');
      btn.disabled = false; btn.textContent = 'Process Payment';
    }
  });
}

// ============================================================
// CLIENTS
// ============================================================
function initClients() {
  const clientForm = document.getElementById('clientForm');
  if (!clientForm) return;

  clientForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    const data = serializeForm(this);
    try {
      const result = await apiPost('/api/clients', data);
      showToast('Client created successfully', 'success');
      setTimeout(() => location.reload(), 800);
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

// ============================================================
// APPOINTMENTS
// ============================================================
function initAppointments() {
  // Status update buttons
  document.querySelectorAll('.appt-status-btn').forEach(btn => {
    btn.addEventListener('click', async function() {
      const apptId = this.dataset.apptId;
      const status = this.dataset.status;
      try {
        const fd = new FormData();
        fd.append('status', status);
        await fetch(`/api/appointments/${apptId}/status`, {
          method: 'PUT', body: fd,
        });
        showToast(`Appointment ${status}`, 'success');
        setTimeout(() => location.reload(), 500);
      } catch (err) {
        showToast('Failed to update', 'error');
      }
    });
  });

  const bookingForm = document.getElementById('bookingForm');
  if (bookingForm) {
    bookingForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      const data = serializeForm(this);
      const payload = {
        client_id: data.client_id,
        stylist_id: data.stylist_id,
        service_id: data.service_id,
        start_time: data.start_time,
        notes: data.notes || '',
      };
      try {
        const result = await apiPost('/api/appointments', payload);
        showToast('Appointment booked!', 'success');
        setTimeout(() => location.reload(), 800);
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }
}

// ============================================================
// CALENDAR
// ============================================================
function initCalendar() {
  const el = document.getElementById('fullCalendar');
  if (!el || typeof FullCalendar === 'undefined') return;

  const stylistFilter = document.getElementById('stylistFilter');

  const calendar = new FullCalendar.Calendar(el, {
    initialView: 'timeGridWeek',
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'dayGridMonth,timeGridWeek,timeGridDay',
    },
    slotMinTime: '08:00:00',
    slotMaxTime: '20:00:00',
    slotDuration: '00:30:00',
    allDaySlot: false,
    height: 'auto',
    themeSystem: {
      button: {
        today: { text: 'Today' },
        dayGridMonth: { text: 'Month' },
        timeGridWeek: { text: 'Week' },
        timeGridDay: { text: 'Day' },
      }
    },
    events: function(fetchInfo, successCallback, failureCallback) {
      const params = new URLSearchParams({
        start: fetchInfo.startStr,
        end: fetchInfo.endStr,
      });
      if (stylistFilter?.value) params.append('stylist_id', stylistFilter.value);

      fetch(`/api/appointments/calendar?${params}`)
        .then(r => r.json())
        .then(data => successCallback(data))
        .catch(err => failureCallback(err));
    },
    eventClick: function(info) {
      const props = info.event.extendedProps;
      const modal = document.getElementById('apptDetailModal');
      if (!modal) return;
      modal.querySelector('.appt-client').textContent = props.client || '';
      modal.querySelector('.appt-service').textContent = props.service || '';
      modal.querySelector('.appt-stylist').textContent = props.stylist || '';
      modal.querySelector('.appt-status').textContent = props.status || '';
      modal.querySelector('.appt-notes').textContent = props.notes || '';
      openModal(modal);
    },
  });

  calendar.render();

  if (stylistFilter) {
    stylistFilter.addEventListener('change', () => calendar.refetchEvents());
  }
}

// ============================================================
// INVENTORY
// ============================================================
function initInventory() {
  const form = document.getElementById('inventoryForm');
  if (!form) return;

  form.addEventListener('submit', async function(e) {
    e.preventDefault();
    const fd = new FormData(this);
    try {
      const result = await apiPost('/api/inventory', fd);
      showToast(`${result.item.name} added to inventory`, 'success');
      setTimeout(() => location.reload(), 800);
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  document.querySelectorAll('.stock-update-btn').forEach(btn => {
    btn.addEventListener('click', async function() {
      const itemId = this.dataset.itemId;
      const qty = prompt('Change stock by (+/-):');
      if (!qty) return;
      const fd = new FormData();
      fd.append('quantity', parseInt(qty));
      try {
        await fetch(`/api/inventory/${itemId}/stock`, { method: 'PUT', body: fd });
        showToast('Stock updated', 'success');
        setTimeout(() => location.reload(), 500);
      } catch (err) {
        showToast('Failed to update', 'error');
      }
    });
  });
}
