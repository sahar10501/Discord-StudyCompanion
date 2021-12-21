let check_user_button = document.querySelectorAll('.session_invite')
let div_users = document.getElementById('invite_list');
check_user_button.forEach((element, index) => {
    element.addEventListener('click', function(){
        let user_check = {'user_id': this.value}
        user_check = JSON.stringify(user_check)
        fetch('/', {
            method: 'post',
            body: user_check,
            headers: new Headers({
                'content-type': 'application/json',
                'X-Custom-Header': 'check_user'
            })
        })
        .then(function(response){
            return response.text();
        })
        .then(function(data){
            if (data == 'Joined'){
                let msg = document.getElementById('msg'+index)
                let content = document.createElement('div');
                let avatar_hash = element.getAttribute('data-avatar_id')
                let username = element.getAttribute('data-username')
                content.className = 'row justify-content-center pb-4 pt-3 border-bottom'
                content.innerHTML += `<div style='text-align: center;' class='col-xs-6 col-sm-3'>
                <img src='https://cdn.discordapp.com/avatars/${element.value}/${avatar_hash}.webp?size=1024'
                onerror="this.onerror=null;this.src='https://upload.wikimedia.org/wikipedia/commons/thumb/1/1f/Blank_square.svg/2048px-Blank_square.svg.png';"
                class='img-responsive rounded-circle' alt='User Image' width='125' height='125'>
                <h4 style='color: Gray; margin-top: 1rem;'>${username}</h4>
                <span class='text-muted'>Joined</span>
                </div>`
                div_users.appendChild(content)
                msg.innerHTML = "Joined"
                element.classList.add('disabled')
            
            }
            
        })
        
    })
});


