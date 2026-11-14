from django.shortcuts import render
from django.core.paginator import Paginator
from registration.models import PropertyDocument

def document_list(request):
    documents = PropertyDocument.objects.all().order_by('-uploaded_at')  # Tri par date décroissante
    paginator = Paginator(documents, 10)  # 10 documents par page

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'page_title': 'Documents',
    }
    return render(request, 'dashboard/document_list.html', context)
