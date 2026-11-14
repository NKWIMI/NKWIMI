from django.shortcuts import render

def bad_request_view(request, exception, template_name='400.html'):
    context = {
        'error_code': 400,
        'error_message': "Bad Request",
        'details': "The server cannot process the request due to a client error."
    }
    return render(request, template_name, context, status=400)

def permission_denied_view(request, exception, template_name='403.html'):
    context = {
        'error_code': 403,
        'error_message': "Permission Denied",
        'details': "You don't have permission to access this resource."
    }
    return render(request, template_name, context, status=403)

def page_not_found_view(request, exception, template_name='404.html'):
    context = {
        'error_code': 404,
        'error_message': "Page Not Found",
        'details': "The page you're looking for doesn't exist."
    }
    return render(request, template_name, context, status=404)

def server_error_view(request, template_name='500.html'):
    context = {
        'error_code': 500,
        'error_message': "Server Error",
        'details': "Something went wrong on our end. We're working to fix it!"
    }
    return render(request, template_name, context, status=500)