let theDiv = document.getElementById('invite_list');
let content = document.createElement('div');
content.className = 'row justify-content-center pb-4 pt-3 border-bottom'
let users = []


let current_time = document.getElementById('current_time')
const today = new Date();
const m = new Date();
let minutes = String(m.getMinutes()).padStart(2, '0');
const time = today.getHours() + ":" + minutes + ":" + today.getSeconds();
current_time.innerHTML = time

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
    console.log(user_id)
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
  let topic = document.getElementById('channel_name_html')
  // maps to an array all user id's
  let users_id = {
    'users_id': users.map(e => e.user_id),
    'topic': channel_name.value
  }
  users_id = JSON.stringify(users_id)
  console.log(users_id)
  // post the list of invited users
  fetch('/', {
    method: 'POST',
    body: users_id,
    headers: new Headers({
      'Content-Type': 'application/json',
      'X-Custom-Header': 'invite_list'
    })
  })
  // disables all the invite buttons after inviting users
  buttons.forEach(element =>  {
    element.classList.add('disabled')
  topic.innerText = channel_name.value
  })
})

let session_control = document.getElementById('session_control')
session_control.addEventListener('click', function(){
  session_control.classList.add('disabled')
  // need to add the list of users that accepted the invite and fetch it to the server in order to add as particpants in the db
  let user_id = {'test':''}
  user_id = JSON.stringify(user_id)
  // Stop or Start session
  fetch('/', {
    method: 'POST',
    body: user_id,
    headers: new Headers({
      'Content-Type': 'application/json',
      'X-Custom-Header': session_control.value+'_session'
    })
  })
  .then(function(response){
    if(response.status == 200){
      window.location.href = '/'
  }
    
  })
})

let open_modal = document.getElementById('open_inv_modal')
if (typeof open_modal == "undefined") {
open_modal.addEventListener('click', function() {
  open_modal.classList.add('disabled')
  open_modal.classList.add('disabled')
})
}

let close_modal = document.getElementById('close_inv_modal')
close_modal.addEventListener('click', function() {
  open_modal.classList.remove('disabled')
})
