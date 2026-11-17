/* Helpers for the review form.
 *
 * Two small things: a live character count under the text box, and a limit
 * on how many tags can be ticked. Both rules are also enforced on the
 * server, so this file is only here to make the form nicer to use.
 */
(function () {
  'use strict';

  var form = document.querySelector('.review-form');
  if (!form) return;

  // --- Character count --------------------------------------------------
  var body = form.querySelector('textarea[name="body"]');
  var counter = form.querySelector('[data-char-count]');
  if (body && counter) {
    var min = Number(counter.getAttribute('data-min'));
    var max = Number(counter.getAttribute('data-max'));
    var updateCount = function () {
      var length = body.value.trim().length;
      if (length < min) {
        counter.textContent = length + ' characters. ' + (min - length) + ' more to go.';
      } else {
        counter.textContent = length + ' of ' + max + ' characters.';
      }
    };
    body.addEventListener('input', updateCount);
    updateCount();
  }

  // --- Tag limit ----------------------------------------------------------
  var maxTags = Number(form.getAttribute('data-max-tags'));
  var boxes = Array.prototype.slice.call(form.querySelectorAll('input[name="tags"]'));
  var tagCount = form.querySelector('[data-tag-count]');
  var updateTags = function () {
    var picked = boxes.filter(function (box) { return box.checked; }).length;
    // Once the limit is reached, the unticked boxes are switched off.
    boxes.forEach(function (box) { box.disabled = !box.checked && picked >= maxTags; });
    if (tagCount) tagCount.textContent = picked + ' of ' + maxTags + ' picked.';
  };
  boxes.forEach(function (box) { box.addEventListener('change', updateTags); });
  updateTags();
})();
