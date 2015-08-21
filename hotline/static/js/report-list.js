// Determine the width of the device (desktop or mobile?)
var width = (window.innerWidth > 0) ? window.innerWidth : screen.width;
// Mobile gets a full-page list, while desktop gets a little less than half.
if(width > 1000)
  width = 500;

// Pop out the menu
$("#menu-button").click(function(e){
  e.preventDefault();
  $("#menu-button").animate({ "right": "-100"}, 100);
  $("#menu-button").promise().done(function(){
    $(this).hide();
    $("#report-list").show();
    $("#report-list").animate({ "right": "0"}, "fast");
    $("#report-list").promise().done(function(){
      var _top = $(".reports-table").position();
      var _pages = $(".step-links").parent().height();
      var height = $("#report-table-container").height() - _pages - _top.top;
      $(".reports-table").children().css({"height": height + "px"});
    });
  });
});

// Make the hover action look nice
var htmlstring = $("#menu-button").html();
var timeoutID;
$("#menu-button").hover(function(){
  if(!timeoutID){
    timeoutID = setTimeout(function(){
      timeoutID = null;
      $("#menu-button").html(htmlstring + " List View");
    }, 400);
  }
}, function(){
  clearTimeout(timeoutID);
  timeoutID = null;
  $(this).html(htmlstring);
});

// Close the menu
$("#menu-close-button").click(function(e){
  e.preventDefault();
  var move = -1 * width;
  $("#report-list").animate({ "right": move }, 100);
  $("#report-list").promise().done(function(){
    $("#menu-button").show();
    $("#menu-button").animate({ "right": "0" }, "fast");
    $(this).hide();
  });
});

$(".gmnoprint").hover(function(){
  $("#menu-button").hide();
}, function(){
  $("#menu-button").show();
});
