function noTokensPopup() {
        // Get the modal
    var modal = document.getElementById("myModal");
    // Get the <span> element that closes the modal
    var span = document.getElementsByClassName("close")[0];
    modal.style.display = "block";
    // When the user clicks on <span> (x), close the modal
    span.onclick = function() {
      modal.style.display = "none";
    };
    // When the user clicks anywhere outside of the modal, close it
    window.onclick = function(event) {
      if (event.target == modal) {
        modal.style.display = "none";
      }
    };
}

function handlePaySuccess(resp) {
  let payMsg = document.getElementById('payMsg');
  payMsg.innerText = resp.message;
  console.log(resp)
}

function payArticle(url) {
  let data = {'url': url, 'test': 'test'};
  console.log(data);
  $.ajax({
    type: "POST",
    url: '/finnplus',
    data: JSON.stringify(data),
    dataType: 'json',
    contentType: 'application/json',
    success: handlePaySuccess
  })
}

function myFunction() {
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
    if(scrolled >= 50 && !pay) {
      pay = true;
      document.getElementById("paid").style.visibility = "visible";
      document.getElementById("divider").style.visibility = "hidden";
      payArticle(window.location.href);
      console.log("Pay article");

    }
  }
}

var pay = false;
window.onload = function () {

  myFunction();
  window.onscroll = function () {
    myFunction(paid);
  };
};

