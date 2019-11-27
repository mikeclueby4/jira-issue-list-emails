$.ajax({
  url: document.location.origin + '/rest/api/2/search',
  data: {jql:'watcher = currentUser()'},
  success: function (response) {
    $.each(response.issues, function(i,issue) {
      console.log('Watching ' + issue.key);
    })
  }
});
