import base64
import hashlib
import itertools
import logging
import os
import posixpath
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFilter

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis.db import models
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.template import Context
from django.template.loader import get_template, render_to_string

from hotline.utils import generate_thumbnail


log = logging.getLogger(__name__)


class Report(models.Model):
    # cache the template since Django is so slow at rendering templates and NFS
    # makes it even worse
    TEMPLATE = get_template("reports/_popover.html")

    report_id = models.AutoField(primary_key=True)
    # It may seem odd to have FKs to the species AND category, but in the case
    # where the user doesn't know what species it is, we fall back to just a
    # category (with the reported_species field NULL'd out)
    reported_category = models.ForeignKey("species.Category")
    reported_species = models.ForeignKey("species.Species", null=True, default=None, related_name="+")

    description = models.TextField(verbose_name="Please provide a description of your find")
    location = models.TextField(
        verbose_name="Please provide a description of the area where species was found",
        help_text="""
            For example name the road, trail or specific landmarks
            near the site whether the species was found. Describe the geographic
            location, such as in a ditch, on a hillside or in a streambed. If you
            happen to have taken GPS coordinates, enter them here.
        """
    )
    has_specimen = models.BooleanField(default=False, verbose_name="Do you have a physical specimen?")

    point = models.PointField(srid=4326)
    county = models.ForeignKey('counties.County', null=True)

    created_by = models.ForeignKey("users.User", related_name="reports")
    created_on = models.DateTimeField(auto_now_add=True)

    claimed_by = models.ForeignKey("users.User", null=True, default=None, related_name="claimed_reports")

    # these are copied over from the original site
    edrr_status = models.IntegerField(verbose_name="EDRR Status", choices=[
        (None, '',),
        (0, 'No Response/Action Required',),
        (1, 'Local expert notified',),
        (2, 'Population assessed',),
        (3, 'Population treated',),
        (4, 'Ongoing monitoring',),
        (5, 'Controlled at site'),
    ], default=None, null=True, blank=True)

    # the actual species confirmed by an expert
    actual_species = models.ForeignKey("species.Species", null=True, default=None, related_name="reports")

    is_archived = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False, help_text="This report can be viewed by the public")

    objects = models.GeoManager()

    class Meta:
        db_table = "report"
        ordering = ['-pk']

    def __str__(self):
        if self.species:
            return str(self.species)

        return self.category.name

    def to_json(self):
        image_url = self.image_url
        return {
            "lat": self.point.y,
            "lng": self.point.x,
            "icon": self.icon_url,
            "title": str(self),
            "image_url": image_url,
            "content": self.__class__.TEMPLATE.render(Context({
                "report": self,
                "image_url": image_url,
            })),
        }

    @property
    def icon_color(self):
        return '#999' if self.species is None else self.species.severity.color

    @property
    def icon_rel_path(self):
        """Generate relative icon path.

        This path can be joined to ``MEDIA_ROOT`` or ``MEDIA_URL``.

        Generally, you'd use :meth:`icon_path` or :meth:`icon_url`
        instead of this.

        """
        category = self.category
        key_parts = [category.icon.path if category.icon else '', self.icon_color]
        key = '|'.join(str(p) for p in key_parts)
        key = hashlib.md5(key.encode('utf-8')).hexdigest()
        path = os.path.join('generated_icons', '%s.png' % key)
        return path

    @property
    def icon_path(self):
        """Path to (generated) icon for this report."""
        return os.path.join(settings.MEDIA_ROOT, self.icon_rel_path)

    @property
    def icon_url(self):
        """Get icon URL for this report.

        The icon is composed of a background color based on the species'
        severity and an image from the species' category. If the icon
        doesn't exist on disk, it will be created.

        If you are going to change the design or size of the icon, you
        will need to update the ``generateIcon`` function in
        ``static/js/main.js`` also.

        """
        # XXX: It seems a little weird to generate the icon here.
        self.generate_icon()
        return posixpath.join(settings.MEDIA_URL, self.icon_rel_path)

    def generate_icon(self):
        """Generate icon for this report.

        The file path for the generated icon is based on parameters that
        will change the appearance of the icon. This ensures the icon is
        updated if the report's category changes.

         ____
        |    |  <- Icons look like this and are constructed in the following way:
        | $$ |      + A transparent canvas is created to hold the icon.
        |_  _|      + A square is placed in the canvas so that it is aligned with the top.
          \/        + And an inverted triangle is placed directly under the square to complete the background.
                    + The outline of the two shapes is extracted and converted to the correct color.
                    + The icon image is pasted in the center of a transparent canvas.
                    + And the canvas is pasted in the middle of the background.
                    + And finally, the outline is merged on top of the background.
        """
        if not os.path.exists(self.icon_path):
            icon = self.category.icon
            color = self.icon_color

            # Define some really ugly, hard-coded magic numbers that we need
            GENERATED_ICON_SIZE = (30, 45)
            SQUARE_COORDS = [(0, 0), (30, 30)]
            # The triangle's (inverted) base begins at 1/3 of the image width,
            # and ends at 2/3 the image width
            TRIANGLE_COORDS = [(10, 30), (15, 45), (20, 30)]

            # ICON_OFFSET is needed so the icon shows up in the center
            # of the background, not just the center of the image.
            ICON_OFFSET = (0, -10)
            TRANSPARENT = (0,0,0,0)
            OUTLINE_COLOR = (10,10,10,255)

            # Define the color mode (because the mode has to
            # be the same in order to merge images)
            mode = 'RGBA'

            # Create a new, transparent image as a canvas with the defined mode and size.
            canvas = Image.new(mode, GENERATED_ICON_SIZE, TRANSPARENT)

            # Draw the background for the icon
            background = ImageDraw.Draw(canvas)
            background.rectangle(SQUARE_COORDS, fill=color)
            background.polygon(TRIANGLE_COORDS, fill=color)

            # Filter out the edges if the background and add a
            # nice dark outline to it by traversing pixel by pixel.
            outline = canvas.filter(ImageFilter.FIND_EDGES)
            pixels = outline.load()
            for i in range(outline.size[0]):
                for j in range(outline.size[1]):
                    if pixels[i,j] != TRANSPARENT:
                        # Since our canvas is transparent, any pixel that
                        # isn't transparent is guaranteed to be an edge, and
                        # thus should have it's color changed to the outline color.
                        pixels[i,j] = OUTLINE_COLOR

            img = canvas
            if icon and os.path.exists(icon.path):
                # Before we can use the icon, it needs to be
                # pasted into an image with the same properties
                # as the background image. Otherwise, transparency
                # will not be preserved. To do this we simply create a new image with
                # the same properties as the canvas, and paste the icon into it.
                icon_file = Image.open(icon.path)
                icon_canvas = Image.new(mode, GENERATED_ICON_SIZE)
                icon_canvas.paste(icon_file, ICON_OFFSET)

                # Alpha composite merge is used to ensure transparency
                # is preserved while moving the icon onto the canvas.
                img = Image.alpha_composite(canvas, icon_canvas)
            else:
                log.warn('No icon found for this category')

            # Now merge the image with the outline
            img = Image.alpha_composite(img, outline)

            try:
                img.save(self.icon_path)
            except IOError as e:
                log.warn('Error while saving icon image')

    @property
    def image_url(self):
        """
        Returns the URL to the thumbnail generated for the first public image
        attached to this report or None.

        If the thumbnail doesn't exist, it is created
        """
        for image in itertools.chain(self.image_set.all(), *(comment.image_set.all() for comment in self.comment_set.all())):
            if image.visibility == image.PUBLIC:
                output_path = os.path.join(settings.MEDIA_ROOT, "generated_thumbnails", str(image.pk) + ".png")
                if not os.path.exists(output_path):
                    generate_thumbnail(image.image.path, output_path, width=64, height=64)
                return settings.MEDIA_URL + os.path.relpath(output_path, settings.MEDIA_ROOT)

        return None

    @property
    def species(self):
        """
        Returns the actual species if it exists, and falls back on the reported_species
        """
        return self.actual_species or self.reported_species

    @property
    def category(self):
        """
        Returns the Category of the actual species, falling back to the reported_category
        """
        return self.actual_species.category if self.actual_species else self.reported_category

    @property
    def is_misidentified(self):
        """
        Returns True if the reported_species differs from the actual species (and both fields are filled out)
        """
        return bool(self.reported_species and self.actual_species and self.reported_species != self.actual_species)


class Invite(models.Model):
    """
    Abitrary people can be invited (via email) to leave comments on a report
    """
    invite_id = models.AutoField(primary_key=True)
    # the person invited (a User object will be created for them)
    user = models.ForeignKey("users.User", related_name="invites")
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey("users.User", related_name="+")
    report = models.ForeignKey(Report)

    class Meta:
        db_table = "invite"

    @classmethod
    def create(cls, *, email, report, inviter, message, request):
        """
        Create and send an invitation to the person with the given email address

        Returns True if the invite was sent, otherwise False (meaning the user
        has already been invited before)
        """
        user_model = get_user_model()
        try:
            user = user_model.objects.get(email__iexact=email)
        except user_model.DoesNotExist:
            user = user_model.objects.create(email=email, is_active=False)

        if Invite.objects.filter(user=user, report=report).exists():
            return False

        invite = Invite(user=user, created_by=inviter, report=report)

        send_mail(
            "Invasive Species Hotline Submission Review Request",
            render_to_string("reports/_invite_expert.txt", {
                "inviter": inviter,
                "message": message,
                "url": user.get_authentication_url(request, next=reverse("reports-detail", args=[report.pk]))
            }),
            "noreply@pdx.edu",
            [email]
        )

        invite.save()
        return True


from .indexes import *  # noqa isort:skip
