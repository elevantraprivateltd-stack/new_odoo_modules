/* Helpdesk Custom Module - Client Form (front-end)
 * -------------------------------------------------------------
 * Ye script khud "Client Form" ka HTML banata hai (bilkul ma'am ke diye
 * gaye form ke mutabiq) aur page pe jahan bhi
 *      <div id="hd-ticket-form-mount"></div>
 * milta hai, wahan mount kar deta hai.
 *
 * Submit hone par /helpdesk/ticket/submit ko POST karta hai - jo module
 * ka Python controller receive kar ke helpdesk.ticket (Help Hesk) bana
 * deta hai, aur Client Form ki har value SEEDHI (direct) ticket form ke
 * matching field mein chali jaati hai (Company, Reported By, Designation,
 * State, Domain, Impact, Urgency, Ticket Rating, Description).
 *
 * Isi script/css ko elevantra.cloud (ya kisi bhi external site) par bhi
 * <script src="https://<your-odoo-domain>/ele_helpdesk/static/src/js/helpdesk_contact_form.js"></script>
 * aur
 * <link rel="stylesheet" href="https://<your-odoo-domain>/ele_helpdesk/static/src/css/helpdesk_contact_form.css"/>
 * ke zariye include kar ke, sirf itna div paste karna hai:
 *      <div id="hd-ticket-form-mount"></div>
 * Baaki sab (design + logic) yahin se aata hai.
 */
(function () {
    "use strict";

    // Change this if the form is embedded on a domain other than the
    // Odoo server itself (elevantra.cloud etc.) and needs an absolute URL.
    // Can also be set from the embedding page via: window.HD_SUBMIT_URL = "https://your-odoo-domain/helpdesk/ticket/submit";
    var SUBMIT_URL = window.HD_SUBMIT_URL || '/helpdesk/ticket/submit';

    function buildFormHTML() {
        return (
            '<form id="hd-contact-form" class="hd-contact-form" enctype="multipart/form-data">' +
                '<h2 class="hd-form-title">Client Form</h2>' +

                '<div class="hd-field">' +
                    '<label>Company *</label>' +
                    '<input type="text" name="company" required="required"/>' +
                '</div>' +
                '<div class="hd-field">' +
                    '<label>Reported By *</label>' +
                    '<input type="text" name="reported_by" required="required"/>' +
                '</div>' +
                '<div class="hd-field">' +
                    '<label>Designation</label>' +
                    '<input type="text" name="designation"/>' +
                '</div>' +

                '<div class="hd-row">' +
                    '<div class="hd-field">' +
                        '<label>Email</label>' +
                        '<input type="email" name="email"/>' +
                    '</div>' +
                    '<div class="hd-field">' +
                        '<label>Phone</label>' +
                        '<input type="text" name="phone"/>' +
                    '</div>' +
                '</div>' +

                '<div class="hd-row">' +
                    '<div class="hd-field">' +
                        '<label>State *</label>' +
                        '<select name="state" required="required">' +
                            '<option value="">Select...</option>' +
                            '<option value="new">New</option>' +
                            '<option value="existing">Existing</option>' +
                        '</select>' +
                    '</div>' +
                    '<div class="hd-field">' +
                        '<label>Domain *</label>' +
                        '<select name="domain" required="required">' +
                            '<option value="">Select...</option>' +
                            '<option value="odoo_issue">Odoo Issue</option>' +
                            '<option value="odoo_development">Odoo Development</option>' +
                            '<option value="record_to_report">Record to Report</option>' +
                            '<option value="order_to_cash">Order to Cash</option>' +
                            '<option value="source_to_pay">Source to Pay</option>' +
                        '</select>' +
                    '</div>' +
                '</div>' +

                '<h3 class="hd-section-title">Priority</h3>' +
                '<div class="hd-row">' +
                    '<div class="hd-field">' +
                        '<label>Impact *</label>' +
                        '<select name="impact" id="hd-impact" required="required">' +
                            '<option value="">Select...</option>' +
                            '<option value="high">High</option>' +
                            '<option value="medium">Medium</option>' +
                            '<option value="low">Low</option>' +
                        '</select>' +
                    '</div>' +
                    '<div class="hd-field">' +
                        '<label>Urgency *</label>' +
                        '<select name="urgency" id="hd-urgency" required="required">' +
                            '<option value="">Select...</option>' +
                            '<option value="high">High</option>' +
                            '<option value="medium">Medium</option>' +
                            '<option value="low">Low</option>' +
                        '</select>' +
                    '</div>' +
                '</div>' +

                '<div class="hd-field">' +
                    '<label>Ticket Rating</label>' +
                    '<select name="ticket_rating" id="hd-ticket-rating">' +
                        '<option value="P1">P1</option>' +
                        '<option value="P2">P2</option>' +
                        '<option value="P3">P3</option>' +
                    '</select>' +
                    '<small class="hd-hint">Auto-set from Impact/Urgency - change it if needed.</small>' +
                '</div>' +

                '<div class="hd-field">' +
                    '<label>Description *</label>' +
                    '<textarea name="description" rows="4" required="required"></textarea>' +
                '</div>' +

                '<div class="hd-field">' +
                    '<label>Attachment</label>' +
                    '<input type="file" name="attachment" multiple="multiple"/>' +
                '</div>' +

                '<button type="submit" id="hd-submit-btn">Submit</button>' +
                '<div id="hd-msg" class="hd-msg"></div>' +
            '</form>'
        );
    }

    // Ticket rating comes as a default from Impact + Urgency, but stays changeable.
    var RATING_MAP = {
        'high|high': 'P1', 'high|medium': 'P1', 'medium|high': 'P1',
        'high|low': 'P2', 'low|high': 'P2', 'medium|medium': 'P2',
        'medium|low': 'P3', 'low|medium': 'P3', 'low|low': 'P3'
    };

    function attachHandler(container) {
        var form = container.querySelector('#hd-contact-form');
        var btn = container.querySelector('#hd-submit-btn');
        var msg = container.querySelector('#hd-msg');
        var impactEl = container.querySelector('#hd-impact');
        var urgencyEl = container.querySelector('#hd-urgency');
        var ratingEl = container.querySelector('#hd-ticket-rating');

        function suggestRating() {
            var key = impactEl.value + '|' + urgencyEl.value;
            if (impactEl.value && urgencyEl.value && RATING_MAP[key]) {
                ratingEl.value = RATING_MAP[key];
            }
        }
        impactEl.addEventListener('change', suggestRating);
        urgencyEl.addEventListener('change', suggestRating);

        form.addEventListener('submit', function (ev) {
            ev.preventDefault();
            btn.disabled = true;
            btn.textContent = 'Sending...';
            msg.style.display = 'none';

            var fd = new FormData(form);

            fetch(SUBMIT_URL, {
                method: 'POST',
                body: fd,
            })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    btn.disabled = false;
                    btn.textContent = 'Submit';
                    msg.style.display = 'block';
                    if (data.success) {
                        msg.className = 'hd-msg hd-success';
                        msg.textContent = 'Thank you! Your request (' + data.ticket_ref +
                            ') has been received. We will get back to you soon.';
                        form.reset();
                    } else {
                        msg.className = 'hd-msg hd-error';
                        msg.textContent = data.error || 'Something went wrong. Please try again.';
                    }
                })
                .catch(function () {
                    btn.disabled = false;
                    btn.textContent = 'Submit';
                    msg.style.display = 'block';
                    msg.className = 'hd-msg hd-error';
                    msg.textContent = 'Could not reach the server. Please try again.';
                });
        });
    }

    function init() {
        var mounts = document.querySelectorAll('#hd-ticket-form-mount');
        mounts.forEach(function (mount) {
            if (mount.dataset.hdMounted) {
                return;
            }
            mount.dataset.hdMounted = '1';
            mount.innerHTML = buildFormHTML();
            attachHandler(mount);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
