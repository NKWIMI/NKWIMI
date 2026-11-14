# registration/views/parcel_views.py
import logging
import qrcode
from io import BytesIO
import base64

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View, DeleteView
from django.conf import settings

from ..forms.parcel_forms import ParcelRegistrationForm
from ..services.blockchain_service import BlockchainService
from ..services.file_hash_service import FileHashService
from registration.models.parcel_models import Parcel, ParcelMetadata

logger = logging.getLogger(__name__)


class ParcelListView(LoginRequiredMixin, ListView):
    model = Parcel
    template_name = 'registration/parcel_list.html'
    context_object_name = 'parcels'
    paginate_by = 10
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff and not self.request.user.is_superuser:
            # FIX: Use 'owner' field instead of 'owner_address' for user filtering
            qs = qs.filter(owner=self.request.user)
        return qs.select_related('owner').prefetch_related('metadata_versions')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['now'] = timezone.now()
        
        # Add debug information
        ctx['debug'] = True  # Set to False in production
        ctx['user_parcels_count'] = self.get_queryset().count()
        ctx['user_parcels'] = list(self.get_queryset().values_list('land_id', flat=True))
        ctx['user_info'] = {
            'username': self.request.user.username,
            'is_staff': self.request.user.is_staff,
            'is_superuser': self.request.user.is_superuser,
            'blockchain_address': self.request.user.blockchain_address,
        }
        
        # Add additional debug info for parcel ownership verification
        all_user_parcels = Parcel.objects.filter(owner=self.request.user)
        ctx['all_user_parcels_count'] = all_user_parcels.count()
        ctx['all_user_parcels'] = list(all_user_parcels.values('land_id', 'owner__username'))
        
        return ctx


class ParcelDetailView(LoginRequiredMixin, DetailView):
    model = Parcel
    template_name = 'registration/parcel_detail.html'
    context_object_name = 'parcel'

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff and not self.request.user.is_superuser:
            qs = qs.filter(owner=self.request.user)  # Updated to use owner instead of owner_address
        return qs.select_related('owner').prefetch_related('metadata_versions')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user_addr = self.request.user.blockchain_address
        
        ctx['can_edit'] = (
            self.object.owner == self.request.user  # Updated to use owner comparison
            or self.request.user.is_staff
            or self.request.user.is_superuser
        )
        
        # Add debug information
        ctx['debug'] = True
        ctx['parcel_owner_info'] = {
            'parcel_owner_id': self.object.owner.id if self.object.owner else None,
            'parcel_owner_username': self.object.owner.username if self.object.owner else None,
            'current_user_id': self.request.user.id,
            'current_user_username': self.request.user.username,
            'ownership_match': self.object.owner == self.request.user,
        }
        
        return ctx


class ParcelCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Parcel
    form_class = ParcelRegistrationForm
    template_name = 'registration/register_parcel.html'
    # FIXED: Use the correct URL name for parcel list
    #success_url = reverse_lazy('parcel_list')
    success_url = reverse_lazy('parcel:parcel_list')

    def test_func(self):
        return (
            self.request.user.is_authenticated and
            (self.request.user.is_staff or
             self.request.user.is_superuser or
             getattr(self.request.user, "can_register_parcels", False))
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            with transaction.atomic():
                parcel = form.save(commit=False)
                
                # For regular users, ensure they are set as owner
                if not (self.request.user.is_staff or self.request.user.is_superuser):
                    parcel.owner = self.request.user
                    if self.request.user.blockchain_address:
                        parcel.owner_address = self.request.user.blockchain_address
                
                # Handle contract file upload
                if 'contract_file' in self.request.FILES:
                    file_service = FileHashService()
                    parcel.latest_ipfs_hash = file_service.add_file(self.request.FILES['contract_file'])

                # Save the parcel first to get an ID
                parcel.save()

                # Blockchain registration with error handling
                try:
                    blockchain = BlockchainService(self.request.user)
                    tx_hash = blockchain.register_parcel(
                        parcel.land_id,
                        parcel.owner_address,
                        parcel.latest_ipfs_hash or ''
                    )
                    parcel.transaction_hash = tx_hash
                    parcel.save(update_fields=['transaction_hash'])
                    
                    # Create success metadata
                    ParcelMetadata.objects.create(
                        parcel=parcel,
                        ipfs_hash=parcel.latest_ipfs_hash or '',
                        uploader=self.request.user,
                        notes="Initial registration with blockchain",
                    )
                    
                    messages.success(self.request, 'Parcel created and registered on blockchain successfully!')
                    
                except Exception as blockchain_error:
                    # Log blockchain error but don't fail the parcel creation
                    logger.warning("Blockchain registration failed: %s", blockchain_error, exc_info=True)
                    
                    # Create metadata without blockchain reference
                    ParcelMetadata.objects.create(
                        parcel=parcel,
                        ipfs_hash=parcel.latest_ipfs_hash or '',
                        uploader=self.request.user,
                        notes="Initial registration (blockchain registration failed)",
                    )
                    
                    messages.warning(self.request, 'Parcel created successfully but blockchain registration failed. Please try blockchain registration later.')

                return super().form_valid(form)
                
        except Exception as e:
            logger.error("Parcel creation failed: %s", e, exc_info=True)
            messages.error(self.request, f'Error creating parcel: {e}')
            return self.form_invalid(form)


class ParcelDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Parcel
    template_name = 'registration/parcel_confirm_delete.html'
    # FIXED: Use the correct URL name for parcel list
    #success_url = reverse_lazy('parcel_list')
    success_url = reverse_lazy('parcel:parcel_list')
    context_object_name = 'parcel'

    def test_func(self):
        parcel = self.get_object()
        return (
            parcel.owner == self.request.user  # Updated to use owner comparison
            or self.request.user.is_staff
            or self.request.user.is_superuser
        )

    def delete(self, request, *args, **kwargs):
        try:
            parcel = self.get_object()
            parcel_id = parcel.land_id
            
            # Just delete from local database (blockchain data is immutable)
            response = super().delete(request, *args, **kwargs)
            
            if parcel.transaction_hash:
                messages.warning(request, 
                    f"Parcel {parcel_id} deleted from local database. "
                    f"Blockchain record remains immutable at TX: {parcel.transaction_hash}"
                )
            else:
                messages.success(request, f"Parcel {parcel_id} has been deleted successfully.")
                
            return response
            
        except Exception as e:
            logger.error(f"Error deleting parcel: {e}", exc_info=True)
            messages.error(request, f"Error deleting parcel: {e}")
            return redirect('parcel_list')


class RegisterParcelView(ParcelCreateView):
    """Alias for ParcelCreateView for backward compatibility"""
    pass


class ParcelUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Parcel
    form_class = ParcelRegistrationForm
    template_name = 'registration/parcel_update.html'
    context_object_name = 'parcel'

    # FIXED: Use the correct URL name for parcel detail
    def get_success_url(self):
        return reverse_lazy('parcel:parcel_detail', kwargs={'pk': self.object.pk})

    def test_func(self):
        parcel = self.get_object()
        return (
            parcel.owner == self.request.user  # Updated to use owner comparison
            or self.request.user.is_staff
            or self.request.user.is_superuser
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            with transaction.atomic():
                parcel = form.save(commit=False)

                # Handle owner_address synchronization for admin users
                if self.request.user.is_staff or self.request.user.is_superuser:
                    if parcel.owner and parcel.owner.blockchain_address:
                        parcel.owner_address = parcel.owner.blockchain_address

                # Handle contract file upload
                if 'contract_file' in self.request.FILES:
                    file_service = FileHashService()
                    new_ipfs_hash = file_service.add_file(self.request.FILES['contract_file'])
                    if new_ipfs_hash != parcel.latest_ipfs_hash:
                        ParcelMetadata.objects.create(
                            parcel=parcel,
                            ipfs_hash=new_ipfs_hash,
                            uploader=self.request.user,
                            notes=form.cleaned_data.get('change_notes', 'Document updated'),
                        )
                        parcel.latest_ipfs_hash = new_ipfs_hash

                parcel.save()
                messages.success(self.request, 'Parcel updated successfully!')
                return super().form_valid(form)
        except Exception as e:
            logger.error("Parcel update failed: %s", e, exc_info=True)
            messages.error(self.request, f'Error updating parcel: {e}')
            return self.form_invalid(form)


class ParcelPrintView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Parcel
    template_name = 'registration/parcel_print.html'
    context_object_name = 'parcel'

    def test_func(self):
        parcel = self.get_object()
        return (
            parcel.owner == self.request.user  # Updated to use owner comparison
            or self.request.user.is_staff
            or self.request.user.is_superuser
        )

    def get(self, request, *args, **kwargs):
        parcel = self.get_object()
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        # QR code content - link to parcel detail
        # FIXED: Use the correct URL pattern for parcel detail
        qr_data = f"{settings.SITE_URL}/parcels/{parcel.pk}/"
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create QR code image
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_code = base64.b64encode(buffer.getvalue()).decode()
        
        context = {
            'parcel': parcel,
            'qr_code': qr_code,
            'site_url': settings.SITE_URL,
            'generated_date': timezone.now()
        }
        
        # Return HTML that can be printed (you can later add PDF generation)
        html_content = render_to_string(self.template_name, context)
        return HttpResponse(html_content)


class FreezeParcelView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        parcel = get_object_or_404(Parcel, pk=self.kwargs['pk'])
        return (
            parcel.owner == self.request.user  # Updated to use owner comparison
            or self.request.user.is_staff
            or self.request.user.is_superuser
        )

    def post(self, request, *args, **kwargs):
        parcel = get_object_or_404(Parcel, pk=self.kwargs['pk'])
        try:
            with transaction.atomic():
                new_status = not parcel.is_frozen
                parcel.is_frozen = new_status
                parcel.save(update_fields=['is_frozen'])

                # Blockchain operation with error handling
                try:
                    blockchain = BlockchainService(user=request.user)
                    if new_status:
                        tx_hash = blockchain.freeze_parcel(parcel.land_id)
                        msg = f"Parcel {parcel.land_id} frozen successfully."
                    else:
                        tx_hash = blockchain.unfreeze_parcel(parcel.land_id)
                        msg = f"Parcel {parcel.land_id} unfrozen successfully."

                    parcel.transaction_hash = tx_hash
                    parcel.save(update_fields=['transaction_hash'])
                    
                    messages.success(request, msg)
                    
                except Exception as blockchain_error:
                    logger.warning("Blockchain operation failed: %s", blockchain_error, exc_info=True)
                    messages.warning(request, f"Parcel status changed locally but blockchain operation failed: {blockchain_error}")

                ParcelMetadata.objects.create(
                    parcel=parcel,
                    uploader=request.user,
                    notes=f"Parcel {'frozen' if new_status else 'unfrozen'}",
                    is_status_change=True,
                )

        except Exception as e:
            logger.error("Error updating parcel freeze status: %s", e, exc_info=True)
            messages.error(request, f"Error updating parcel: {e}")

        # FIXED: Use the correct URL name for parcel detail
        return redirect('parcel:parcel_detail', pk=parcel.pk)


class ParcelMetadataView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Parcel
    template_name = 'registration/parcel_metadata.html'
    context_object_name = 'parcel'

    def test_func(self):
        parcel = self.get_object()
        return (
            parcel.owner == self.request.user  # Updated to use owner comparison
            or self.request.user.is_staff
            or self.request.user.is_superuser
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['metadata'] = (
            self.object.metadata_versions.all()
            .select_related('uploader')
            .order_by('-created_at')  # Changed from '-timestamp' to '-created_at'
        )
        return ctx