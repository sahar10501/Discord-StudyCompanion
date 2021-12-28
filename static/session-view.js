let current_time = new Date();
let duration_timer = document.getElementById('duration')
let data = duration_timer.getAttribute('data-duration')

let duration_time = data.split('.')[0] + 'Z'
let formatted_dur = new Date(duration_time)

formatted_dur.toLocaleTimeString()
let total_duration = current_time.getTime() - formatted_dur.getTime()

let myInterval = setInterval(myTimer, 1000);
function myTimer() {
    total_duration = total_duration + 1000
    time = msToTime(total_duration)
    time = time.split('.')[0]
    duration_timer.innerText = time
}

function msToTime(duration) {
    var milliseconds = Math.floor((duration % 1000) / 100),
      seconds = Math.floor((duration / 1000) % 60),
      minutes = Math.floor((duration / (1000 * 60)) % 60),
      hours = Math.floor((duration / (1000 * 60 * 60)) % 24);
  
    hours = (hours < 10) ? "0" + hours : hours;
    minutes = (minutes < 10) ? "0" + minutes : minutes;
    seconds = (seconds < 10) ? "0" + seconds : seconds;
  
    return hours + ":" + minutes + ":" + seconds + "." + milliseconds;
  }

  
// console.log(format.toLocaleTimeString()); convert the db time to user time
