frappe.ui.form.on('Grievance', {
	refresh: function (frm) {
		if (!frm.is_new()) {
			load_case_timeline(frm);
		}
	}
});

function load_case_timeline(frm) {
	frm.call('get_case_timeline').then(r => {
		if (r.message && r.message.length) {
			render_timeline(frm, r.message);
		} else {
			frm.fields_dict.case_timeline_html.$wrapper.html(
				'<p class="text-muted" style="padding:10px">No timeline events yet.</p>'
			);
		}
	});
}

function render_timeline(frm, events) {
	const type_config = {
		filed:    { color: '#2490ef', icon: 'fa fa-file-text-o', label: 'Filed' },
		assigned: { color: '#f4811f', icon: 'fa fa-user-o',      label: 'Assigned' },
		atr:      { color: '#36a541', icon: 'fa fa-check-square-o', label: 'ATR' },
		appeal:   { color: '#e24c4c', icon: 'fa fa-gavel',        label: 'Appeal' },
	};

	let rows = events.map((ev, idx) => {
		const cfg = type_config[ev.type] || { color: '#888', icon: 'fa fa-circle-o', label: ev.type };
		const detail_rows = Object.entries(ev.details || {})
			.filter(([, v]) => v)
			.map(([k, v]) => `
				<tr>
					<td style="padding:4px 12px 4px 0;color:#6c757d;white-space:nowrap;vertical-align:top;font-size:12px">${k}</td>
					<td style="padding:4px 0;font-size:12px">${frappe.utils.escape_html(String(v))}</td>
				</tr>`).join('');

		const detail_id = `grs-tl-detail-${frm.doc.name.replace(/[^a-zA-Z0-9]/g, '_')}-${idx}`;

		return `
		<div style="display:flex;align-items:flex-start;margin-bottom:0;position:relative">
			<!-- Spine line -->
			<div style="display:flex;flex-direction:column;align-items:center;margin-right:14px;min-width:36px">
				<div style="width:32px;height:32px;border-radius:50%;background:${cfg.color};display:flex;align-items:center;justify-content:center;flex-shrink:0;z-index:1">
					<i class="${cfg.icon}" style="color:#fff;font-size:14px"></i>
				</div>
				<div style="width:2px;background:#e2e6ea;flex:1;min-height:20px"></div>
			</div>
			<!-- Card -->
			<div style="flex:1;margin-bottom:16px">
				<div
					class="grs-tl-header"
					data-target="${detail_id}"
					style="cursor:pointer;display:flex;align-items:center;justify-content:space-between;
					       background:#f8f9fa;border:1px solid #e2e6ea;border-radius:6px;padding:8px 12px;
					       user-select:none"
					onclick="grs_toggle_timeline_detail('${detail_id}', this)"
				>
					<span>
						<strong style="font-size:13px">${frappe.utils.escape_html(ev.title)}</strong>
						<span style="color:#6c757d;font-size:12px;margin-left:8px">${format_date(ev.date)}</span>
					</span>
					<i class="fa fa-chevron-down grs-tl-chevron" style="color:#aaa;font-size:11px;transition:transform 0.2s"></i>
				</div>
				<div id="${detail_id}" style="display:none;border:1px solid #e2e6ea;border-top:none;border-radius:0 0 6px 6px;padding:10px 14px;background:#fff">
					${detail_rows
						? `<table style="width:100%;border-collapse:collapse">${detail_rows}</table>`
						: '<p class="text-muted" style="margin:0;font-size:12px">No details.</p>'
					}
				</div>
			</div>
		</div>`;
	}).join('');

	const html = `
		<style>
			.grs-tl-header:hover { background:#eef2f7 !important; }
			.grs-tl-chevron.open { transform: rotate(180deg); }
		</style>
		<div style="padding:16px 8px 4px 8px">
			${rows}
		</div>`;

	frm.fields_dict.case_timeline_html.$wrapper.html(html);
}

window.grs_toggle_timeline_detail = function (id, header) {
	const el = document.getElementById(id);
	if (!el) return;
	const chevron = header.querySelector('.grs-tl-chevron');
	if (el.style.display === 'none') {
		el.style.display = 'block';
		if (chevron) chevron.classList.add('open');
	} else {
		el.style.display = 'none';
		if (chevron) chevron.classList.remove('open');
	}
};

function format_date(date_str) {
	if (!date_str) return '';
	try {
		return frappe.datetime.str_to_user(date_str.substring(0, 10));
	} catch (e) {
		return date_str;
	}
}
