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
                let status = document.getElementById('status'+index)
                status.innerText = 'Joined'
                element.classList.add('disabled')
                theDiv.style.marginTop = null;
                msg.innerHTML = "Joined"

            }
            else {
                let spanTag = document.createElement('SPAN');
                spanTag.setAttribute('id', 'loading_span')
                spanTag.className = 'spinner-grow spinner-grow-sm'
                element.innerHTML = 'Checking'
                element.appendChild(spanTag)
                element.classList.add('disabled')
                setTimeout(() => {element.classList.remove('disabled'); element.removeChild(spanTag); element.innerText = 'Check Status'}, 4000)
            }
        })
    })
});
