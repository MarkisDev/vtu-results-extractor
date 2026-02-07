/*
* Main JS file
* Core JS functions for UI
* @author: Rijuth Menon
* @copyright: https://rijuthmenon.me
*/

// For Toastr
toastr.options = {
    "closeButton": true,
    "debug": false,
    "newestOnTop": true,
    "progressBar": true,
    "positionClass": "toast-top-right",
    "preventDuplicates": false,
    "onclick": null,
    "showDuration": "900",
    "hideDuration": "1000",
    "timeOut": "5000",
    "extendedTimeOut": "1500",
    "showEasing": "swing",
    "hideEasing": "linear",
    "showMethod": "fadeIn",
    "hideMethod": "fadeOut"
}

function extract()
{
    document.getElementById("starting").style.display = "block";
    document.getElementById("starting").textContent = "Begining with extraction..."
    var resultLink = document.getElementById('link').value;
    var usn = document.getElementById('usn').value;
    var reval = document.getElementById('reval').checked;
    if (!/https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)/.test(resultLink))
    {
        toastr["error"]("", "Please enter a valid link!");
    }
    else if (!/^\w+(,\w+)*$/.test(usn))
    {
        toastr["error"]("", "Please enter valid USN's!");
    }
    else
    {
        eel.extract(usn, resultLink, reval)(function (ret)
        {
            if (ret.status)
            {
                localStorage.setItem('skipped', ret.skipped)
                localStorage.setItem('len', ret.len)
                window.location.replace('done.html')
            }
            else
            {
                toastr["error"]("", "Error occured while extracting!");
            }
        });
    }

}

function generate()
{



    eel.generate()(function (ret)
    {
        if (ret.status)
        {
            localStorage.setItem('skipped', ret.skipped)
            localStorage.setItem('len', ret.len)
            window.location.replace('done.html')
        }
        else
        {
            toastr["error"]("", "Error occured while generating!");
        }
    });

}

function truncate()
{
    Swal.fire({
        title: 'Are you sure?',
        html: "You will <b>lose all data</b> extracted so far!<br/>Please be careful!",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33',
        confirmButtonText: 'Yes, delete it!'
    }).then((result) =>
    {
        if (result.isConfirmed)
        {
            eel.truncate()(function (ret)
            {
                if (ret.status)
                {
                    Swal.fire(
                        'Deleted!',
                        'Data has been erased!',
                        'success'
                    )
                }
                else
                {
                    Swal.fire(
                        'Error!',
                        'An error occured!',
                        'error'
                    )
                }

            });
        }


    });
}