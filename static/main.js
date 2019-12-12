
function handlePaySuccess(resp) {
  let payMsg = document.getElementById('payMsg');
  payMsg.innerText = resp.message;
}

function handlePayFail(xhr, ajaxOptions, thrownError) {
  location.reload();
}

function payArticle(url) {
  let data = {'url': url};
  console.log(data);
  $.ajax({
    type: "POST",
    url: '/finnplus',
    data: JSON.stringify(data),
    dataType: 'json',
    contentType: 'application/json',
    success: handlePaySuccess,
    error: handlePayFail
  })
}

function payArticleOnPercent(scrolled, percent=50) {
  if (scrolled >= percent && !pay) {
    payArticle(window.location.href);
    pay = true;
    document.getElementById("paid").innerHTML= "&#10004 paid";
    document.getElementById("divider").style.borderColor = "#021E72";
  }
}

function payOnScroll() {
  var scrolled = 0;
  var winScroll =  window.pageYOffset || document.body.scrollTop || document.documentElement.scrollTop || 0;
  var height = document.body.scrollHeight - document.body.clientHeight;
  if (height === 0) {
    scrolled = 100;
  } else {
    scrolled = (winScroll / height) * 100;
  }
  let bar = document.getElementById("myBar");
  if (bar != null) {
    bar.style.width = scrolled + "%";
  }
  /*if(scrolled < 50 ){
    document.getElementById("tillPayment").innerHTML = `${100 - Math.round(scrolled)*2}% till payment`
  }*/

  return scrolled
}

var pay = false;
window.onload = function () {
  payOnScroll();
  window.onscroll = function () {
    payArticleOnPercent(payOnScroll())
  };
};

