let theDiv = document.getElementById('invite_list');
let content = document.createElement('div');
content.className = 'row justify-content-center pb-4 pt-3 border-bottom'
let users = []

// populates the row with all of the assigned users
function show_users() {
  content.innerText = ""
  users.forEach(function(element) {
    content.innerHTML += `<div style='text-align: center;' class='col-xs-6 col-sm-3'>
  <img src='https://cdn.discordapp.com/avatars/${element.user_id}/${element.avatar_hash}.webp?size=1024'
  onerror="this.onerror=null;this.src='https://upload.wikimedia.org/wikipedia/commons/thumb/1/1f/Blank_square.svg/2048px-Blank_square.svg.png';"
  class='img-responsive rounded-circle' alt='User Image' width='125' height='125'>
  <h4 style='color: Gray; margin-top: 1rem;'>${element.name}</h4>
  <span class='text-muted'>Assigned</span>
</div>`
    theDiv.appendChild(content);
  });
}

let buttons = document.querySelectorAll('.user_buttons.btn.btn-primary')
// Listens to button click, assign and remove users from invite list
buttons.forEach(element =>  {
  element.state = 0
  element.addEventListener('click', function() {
    let avatar_id = element.getAttribute('data-avatar_id')
    let user_id = element.getAttribute('data-user_id')
    let username = this.value
      // checking if the button is in invite state
      if (element.state == 0) {
        // preparing a dict with all the user info
        dict =  {
            "user_id": user_id,
            "name": username,
            "avatar_hash": avatar_id,
          }

        // checking for user_id duplicates and limiting array to 4 users
        if (users.length <= 3){
          if (!users.some(user => user.user_id == user_id)) {
            users.push(dict)
            show_users();
          }
          element.state = 1
          element.style.color = 'gray'
          element.innerText = 'Remove'
        };
      }

      else if (element.state == 1){
        users = users.filter(function (e) {
        return e.user_id != user_id
        });
        element.style.color = 'white'
        element.innerText = 'Invite'
        element.state = 0
        show_users();
      };
  })
})

let invite_button = document.getElementById('invite_button')
invite_button.addEventListener('click', function() {
  let channel_name = document.getElementById('channel_name')
  // maps to an array all user id's
  let users_id = {
    'users_id': users.map(e => e.user_id),
    'topic': channel_name.value
  }
  users_id = JSON.stringify(users_id)
  console.log(users_id)
  fetch('/', {
    method: 'POST',
    body: users_id,
    headers: new Headers({
      'Content-Type': 'application/json',
      'X-Custom-Header': 'invite_list'
    })
  })
  .then(function(response){
    return response.text()
  })
  .then(function(data){
    console.log(data);
  })
  buttons.forEach(element =>  {
    element.classList.add('disabled')
  })
})

let open_modal = document.getElementById('open_inv_modal')
open_modal.addEventListener('click', function() {
  open_modal.state = 1
  open_modal.classList.add('disabled')
})

let close_modal = document.getElementById('close_inv_modal')
close_modal.addEventListener('click', function() {
  open_modal.classList.remove('disabled')
})

