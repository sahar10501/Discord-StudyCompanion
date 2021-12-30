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
  onerror="this.onerror=null;this.src='https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_640.png';"
  class='img-responsive rounded-circle' alt='User Image' width='125' height='125'>
  <h4 style='color: Gray; margin-top: 1rem;'>${element.name}</h4>
  <span class='text-muted'>Invited</span>
</div>`
    theDiv.appendChild(content);
    theDiv.style.marginTop = null;
  });
}

let buttons = document.querySelectorAll('.user_buttons.btn')
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
        }

      }
      else if (element.state == 1){
        users = users.filter(function(e) {
        return e.user_id != user_id
        });
        element.style.color = 'white'
        element.innerText = 'Invite'
        element.state = 0
        show_users();
        if (users.length == 0){ 
          theDiv.style.marginTop = '21.5%'
    
      }
      };
  })
})

let invite_button = document.getElementById('invite_button')
invite_button.addEventListener('click', function() {
  if (users.length > 0){
  let channel_name = document.getElementById('channel_name')
  let desc = document.getElementById('description')
  let topic = document.getElementById('channel_name_html')
  // maps to an array all user id's
  let users_id = {
    'users_id': users.map(e => e.user_id),
    'topic': channel_name.value,
    'desc': desc.value
  }
  users_id = JSON.stringify(users_id)
  // post the list of invited users
  fetch('/', {
    method: 'POST',
    body: users_id,
    headers: new Headers({
      'Content-Type': 'application/json',
      'X-Custom-Header': 'stage_session'
    })
  })
  .then(function(response){
    if(response.status == 200){
      open_start_modal.classList.remove('disabled')
  }
  })
  // disables all the invite buttons after inviting users
  buttons.forEach(element =>  {
    element.classList.add('disabled')
  topic.innerText = channel_name.value
  })}
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

let open_inv_modal = document.getElementById('open_inv_modal')
// Need to add the modal with the JS code for the click inv_button event
// if is unneeded
open_inv_modal.addEventListener('click', function() {
  if (users.length != 0){
  open_inv_modal.classList.add('disabled')
}
})


let close_inv_modal = document.getElementById('close_inv_modal')
close_inv_modal.addEventListener('click', function() {
  open_inv_modal.classList.remove('disabled')
})

let open_start_modal = document.getElementById('open_start_modal')
open_start_modal.state = 0
open_start_modal.addEventListener('click', function(){
  
  let user_table = document.getElementById('inv_user_tbl')
  if (open_start_modal.state == 0){
    open_start_modal.state++
    for (let i = 0; i < users.length; i++){
      let row = user_table.insertRow();
      var cell = row.insertCell(0)
      cell.innerHTML = i+1;
      let cell1 = row.insertCell()
      if (users[i]['avatar_hash'] != 'None') {
        let img_url = 'https://cdn.discordapp.com/avatars/' + users[i]['user_id'] + '/' + users[i]['avatar_hash'] + '.webp?size=1024'
        cell1.innerHTML = '<img width="25" height="25" class="img-responsive rounded-circle" alt="User Image" src="' + img_url +  '"> ' + users[i]['name']
      }
      else {
        cell1.innerHTML = '<img src="https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_640.png" width="25" height="25" class=" img-responsive rounded-circle" alt="not found user img" > '
        + users[i]['name']
      }
      let cell2 = row.insertCell()
      cell2.id = 'status'+i
      cell2.innerHTML = 'Invited';
      let cell3 = row.insertCell()
      cell3.innerHTML = "<button type='button' style='background-color: #7ccfff;' value='"+users[i]['user_id']+"'class='btn btn-outline btn-sm'>Check Status</button>";
    }
  }
  let check_button = document.querySelectorAll('.btn.btn-outline.btn-sm')
  check_button.forEach((element, index) => {
    element.addEventListener('click', function(){
      let user_check = {'user_id': this.value}
      user_check = JSON.stringify(user_check)
      fetch('/', {
        method: 'POST',
        body: user_check,
        headers: new Headers({
          'Content-Type': 'application/json',
          'X-Custom-Header': 'check_user'
        })
      })
      .then(function(response) {
        return response.text();
      })
      .then(function(data) {
        if (data == "Invited"){
          let spanTag = document.createElement("SPAN"); 
          spanTag.setAttribute('id', 'loading_span')
          spanTag.className = "spinner-grow spinner-grow-sm"
          element.innerHTML = "Checking"
          element.appendChild(spanTag)
          element.classList.add('disabled')
          setTimeout(() => {element.classList.remove('disabled'); element.removeChild(spanTag); element.innerText = 'Check Again'}, 5000)

        }
        else {
          element.classList.add('disabled')
          element.innerText = "Ready!"
          let status = document.getElementById('status'+index)
          status.innerHTML = "Joined"
        }
      })
    })
  })
})
