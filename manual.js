// Grasph Field Manual - intern pack: top bar and the page contents list.
(function () {
  var mh = document.getElementById("mh");
  if (mh) {
    mh.innerHTML = '<div class="row"><a class="brand" href="#">Grasph <b>Field Manual</b></a><nav><a class="on" href="#">Olist graph on Grasph: the dump and the data</a></nav></div>';
  }

  var toc = document.getElementById("toc");
  if (toc) {
    var html = "<h4>On this page</h4>";
    document.querySelectorAll("main section > h2").forEach(function (h, i) {
      var sec = h.parentElement;
      if (!sec.id) sec.id = "s" + (i + 1);
      var tk = h.querySelector(".tk");
      var label = h.textContent.replace(tk ? tk.textContent : "", "").trim();
      html += '<a href="#' + sec.id + '">' + (tk ? "<span>" + tk.textContent.replace("TASK ", "") + "</span>" : "") + label + "</a>";
    });
    toc.innerHTML = html;
  }
})();
