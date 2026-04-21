frappe.ui.form.on('Book', {

    refresh: function(frm) {
        // Show available copies as colored dashboard indicator
        if (!frm.doc.__islocal) {
            let color = frm.doc.available_copies > 0 ? 'green' : 'red';
            frm.dashboard.add_indicator(
                `Available Copies: ${frm.doc.available_copies} / ${frm.doc.total_copies}`,
                color
            );
        }
        // NOTE: We do NOT set read_only here anymore
        // available_copies is controlled by Python code via frappe.db.set_value
        // but Administrator can still manually correct it if needed
    },

    total_copies: function(frm) {
        // When adding a NEW book, auto-set available = total
        if (frm.doc.__islocal) {
            frm.set_value('available_copies', frm.doc.total_copies);
        }
    }

});
